#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
glider_dac/models/deployment.py
Model definition for a Deployment
'''
from glider_dac import app, db, slugify, queue, redis_connection
from glider_dac.glider_emails import glider_deployment_check
from datetime import datetime, timedelta
from flask_mongokit import Document
from bson.objectid import ObjectId
from rq.job import Job
from rq.exceptions import NoSuchJobError
from shutil import rmtree
import os
import glob
import hashlib


@db.register
class Deployment(Document):
    __collection__ = 'deployments'
    use_dot_notation = True
    use_schemaless = True

    structure = {
        'name': str,
        'user_id': ObjectId,
        'username': str,  # The cached username to lightly DB load
        # The operator of this Glider. Shows up in TDS as the title.
        'operator': str,
        'deployment_dir': str,
        'estimated_deploy_date': datetime,
        'estimated_deploy_location': str,  # WKT text
        'wmo_id': str,
        'completed': bool,
        'created': datetime,
        'updated': datetime,
        'glider_name': str,
        'deployment_date': datetime,
        'archive_safe': bool,
        'checksum': str,
        'attribution': str,
        'delayed_mode': bool,
        'latest_file': str,
        'latest_file_mtime': datetime,
    }

    default_values = {
        'created': datetime.utcnow,
        'completed': False,
        'archive_safe': True,
        'delayed_mode': False,
    }

    indexes = [
        {
            'fields': 'name',
            'unique': True,
        },
    ]

    def save(self):
        if self.username is None or self.username == '':
            user = db.User.find_one({'_id': self.user_id})
            self.username = user.username


        # Update the stats on the latest profile file
        modtime = None
        latest_file = self.get_latest_nc_file()
        if latest_file:  # if there are indeed files, get name and modtime
            modtime = datetime.fromtimestamp(os.path.getmtime(latest_file))
            latest_file = os.path.basename(latest_file)
        self.latest_file = latest_file
        self.latest_file_mtime = modtime

        self.sync()
        self.updated = datetime.utcnow()
        app.logger.info("Update time is %s", self.updated)
        update_vals = dict(self)
        try:
            doc_id = update_vals.pop("_id")
        # if we get a KeyError, this is a new deployment that hasn't been entered into the database yet
        # so we need to save it.  This is when you add "New deployment" while logged in -- files must
        # later be added
        except KeyError:
            Document.save(self)
        # otherwise, need to use update/upsert via Pymongo in case of queued job for
        # compliance so that result does not get clobbered.
        # use $set instead of replacing document
        else:
            db.deployments.update({"_id": doc_id}, {"$set": update_vals}, upsert=True)
        # HACK: special logic for Navy gliders deployment
        if self.username == "navoceano" and self.glider_name.startswith("ng"):
            glob_path = os.path.join(app.config.get('DATA_ROOT'),
                                     "hurricanes-20230601T000",
                                     f"{self.glider_name}*")
            for deployment_file in glob.iglob(glob_path):
                symlink_dest = os.path.join('deployment_dir',
                                            deployment_file.name.replace("_", "-"))
                try:
                    os.symlink(deployment_file, symlink_dest)
                except OSError:
                    app.logger.exception(f"Could not symlink {symlink_dest}")

    def delete(self):
        if os.path.exists(self.full_path):
            rmtree(self.full_path)
        if os.path.exists(self.public_erddap_path):
            rmtree(self.public_erddap_path)
        if os.path.exists(self.thredds_path):
            rmtree(self.thredds_path)
        Document.delete(self)

    @property
    def dap(self):
        '''
        Returns the THREDDS DAP URL to this deployment
        '''
        args = {
            'host': app.config['THREDDS'],
            'user': slugify(self.username),
            'deployment': slugify(self.name)
        }
        dap_url = "http://%(host)s/thredds/dodsC/deployments/%(user)s/%(deployment)s/%(deployment)s.nc3.nc" % args
        return dap_url

    @property
    def sos(self):
        '''
        Returns the URL to the NcSOS endpoint
        '''
        args = {
            'host': app.config['THREDDS'],
            'user': slugify(self.username),
            'deployment': slugify(self.name)
        }
        sos_url = "http://%(host)s/thredds/sos/deployments/%(user)s/%(deployment)s/%(deployment)s.nc3.nc?service=SOS&request=GetCapabilities&AcceptVersions=1.0.0" % args
        return sos_url

    @property
    def iso(self):
        name = slugify(self.name)
        iso_url = 'http://%(host)s/erddap/tabledap/%(name)s.iso19115' % {
            'host': app.config['PUBLIC_ERDDAP'], 'name': name}
        return iso_url

    @property
    def thredds(self):
        args = {
            'host': app.config['THREDDS'],
            'user': slugify(self.username),
            'deployment': slugify(self.name)
        }
        thredds_url = "http://%(host)s/thredds/catalog/deployments/%(user)s/%(deployment)s/catalog.html?dataset=deployments/%(user)s/%(deployment)s/%(deployment)s.nc3.nc" % args
        return thredds_url

    @property
    def erddap(self):
        args = {
            'host': app.config['PUBLIC_ERDDAP'],
            'user': slugify(self.username),
            'deployment': slugify(self.name)
        }
        erddap_url = "http://%(host)s/erddap/tabledap/%(deployment)s.html" % args
        return erddap_url

    @property
    def title(self):
        if self.operator is not None and self.operator != "":
            return self.operator
        else:
            return self.username

    @property
    def full_path(self):
        return os.path.join(app.config.get('DATA_ROOT'), self.deployment_dir)

    @property
    def public_erddap_path(self):
        return os.path.join(app.config.get('PUBLIC_DATA_ROOT'), self.deployment_dir)

    @property
    def thredds_path(self):
        return os.path.join(app.config.get('THREDDS_DATA_ROOT'), self.deployment_dir)

    def on_complete(self):
        """
        sync calls here to trigger any completion tasks.

        - write or remove complete.txt
        - generate/update md5 files (removed on not-complete)
        - link/unlink via bindfs to archive dir
        - schedule checker report against ERDDAP endpoint
        """
        # Save a file called "completed.txt"
        completed_file = os.path.join(self.full_path, "completed.txt")
        if self.completed is True:
            with open(completed_file, 'w') as f:
                f.write(" ")
        else:
            if os.path.exists(completed_file):
                os.remove(completed_file)

        # generate md5s of all data files on completion
        if self.completed:
            # schedule the checker job to kick off the compliance checker email
            # on the deployment when the deployment is completed
            # on_complete might be a misleading function name -- this section
            # can run any time there is a sync, so check if a checker run has already been executed
            # if compliance check failed or has not yet been run, go ahead to next section
            ccheck_job_id = f"{self.name}_compliance_check"
            # rerun a compliance check if unrun or failed and there is no
            # other scheduled job already queued up
            if not getattr(self, "compliance_check_passed", False):
                try:
                    job = Job.fetch(id=ccheck_job_id, connection=redis_connection)
                # if no job exists, continue on
                except NoSuchJobError:
                    pass
                # if the job already exists, do nothing -- it will run later
                else:
                    app.logger.info("Deferred compliance check job already scheduled "
                                    f"for deployment {self.name}, skipping...")
                    return

                app.logger.info("Scheduling compliance check for completed "
                                "deployment {}".format(self.deployment_dir))
                queue.enqueue_in(timedelta(minutes=30), glider_deployment_check,
                                 kwargs={"deployment_dir": self.deployment_dir},
                                 job_id=ccheck_job_id, job_timeout=800)
        else:
            for dirpath, dirnames, filenames in os.walk(self.full_path):
                for f in filenames:
                    if f.endswith(".md5"):
                        # FIXME? this doesn't create md5sums, it removes them
                        os.unlink(os.path.join(dirpath, f))

    def get_latest_nc_file(self):
        '''
        Returns the latest netCDF file found in the directory

        :param str root: Root of the directory to scan
        '''
        list_of_files = glob.glob('{}/*.nc'.format(self.full_path))
        if not list_of_files:  # Check for no files
            return None
        return max(list_of_files, key=os.path.getmtime)

    def calculate_checksum(self):
        '''
        Calculates a checksum for the deployment based on the MongoKit to_json()
        serialization and the modified time(s) of the dive file(s).
        '''
        md5 = hashlib.md5()
        # Now add the modified times for the dive files in the deployment directory
        # We dont MD5 every dive file here to save time
        for dirpath, dirnames, filenames in os.walk(self.full_path):
            for f in filenames:
                # could simply do `not f.endswith(.nc)`
                if (f in ["deployment.json", "wmoid.txt", "completed.txt"]
                    or f.endswith(".md5") or not f.endswith('.nc')):
                    continue
                mtime = os.path.getmtime(os.path.join(dirpath, f))
                mtime = datetime.utcfromtimestamp(mtime)

                md5.update(mtime.isoformat().encode('utf-8'))
        self.checksum = md5.hexdigest()

    def sync(self):
        if app.config.get('NODATA'):
            return
        if not os.path.exists(self.full_path):
            try:
                os.makedirs(self.full_path)
            except OSError:
                pass

        # trigger any completed tasks if necessary
        self.update_wmoid_file()
        self.on_complete()
        self.calculate_checksum()

        # Serialize Deployment model to disk
        json_file = os.path.join(self.full_path, "deployment.json")
        with open(json_file, 'w') as f:
            f.write(self.to_json())

    def update_wmoid_file(self):
        # Keep the WMO file updated if it is edited via the web form
        wmo_id = ""
        if self.wmo_id is not None and self.wmo_id != "":
            wmo_id_file = os.path.join(self.full_path, "wmoid.txt")
            if os.path.exists(wmo_id_file):
                # Read the wmo_id from file
                with open(wmo_id_file, 'r') as f:
                    wmo_id = str(f.readline().strip())

            if wmo_id != self.wmo_id:
                # Write the new wmo_id to file if new
                with open(wmo_id_file, 'w') as f:
                    f.write(self.wmo_id)
    @classmethod
    def get_deployment_count_by_operator(cls):
        return [count for count in db.deployments.aggregate({'$group': {'_id':
                                                                        '$operator',
                                                                        'count':
                                                                        {'$sum':
                                                                         1}}},
                                                            cursor={})]
