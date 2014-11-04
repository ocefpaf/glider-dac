import os
import urllib
import hashlib
import subprocess
import warnings

from glider_dac import app, db, slugify
from datetime import datetime
from flask.ext.mongokit import Document
from bson.objectid import ObjectId
from glider_dac.defaults import PUBLIC_ERDDAP, THREDDS

@db.register
class Deployment(Document):
    __collection__   = 'deployments'
    use_dot_notation = True
    use_schemaless   = True

    structure = {
        'name'                      : unicode,
        'user_id'                   : ObjectId,
        'username'                  : unicode,  # The cached username to lightly DB load
        'operator'                  : unicode,  # The operator of this Glider. Shows up in TDS as the title.
        'deployment_dir'               : unicode,
        'estimated_deploy_date'     : datetime,
        'estimated_deploy_location' : unicode,  # WKT text
        'wmo_id'                    : unicode,
        'completed'                 : bool,
        'created'                   : datetime,
        'updated'                   : datetime
    }

    default_values = {
        'created': datetime.utcnow,
        'completed': False
    }

    indexes = [
        {
            'fields': 'name',
            'unique': True,
        },
    ]

    def save(self):
        if self.username is None or self.username == u'':
            user = db.User.find_one( { '_id' : self.user_id } )
            self.username = user.username

        self.updated = datetime.utcnow()

        self.sync()
        super(Deployment, self).save()

    @property
    def dap(self):
        '''
        Returns the THREDDS DAP URL to this deployment
        '''
        args = { 
            'host' : THREDDS, 
            'user' : slugify(self.username), 
            'deployment' : slugify(self.name)
        }
        dap_url = u"http://%(host)s/thredds/dodsC/%(user)s/%(deployment)s.nc3.nc" % args
        return dap_url

    @property
    def sos(self):
        '''
        Returns the URL to the NcSOS endpoint
        '''
        args = { 
            'host' : THREDDS, 
            'user' : slugify(self.username), 
            'deployment' : slugify(self.name)
        }
        sos_url = u"http://%(host)s/thredds/sos/%(user)s/%(deployment)s.nc3.nc?service=SOS&request=GetCapabilities&AcceptVersions=1.0.0" % args
        return sos_url

    @property
    def iso(self):
        title = slugify(self.title)
        name = slugify(self.name)
        iso_url = u'http://%(host)s/erddap/tabledap/%(name)s.iso19115' % {'host' : PUBLIC_ERDDAP, 'name' : name}
        return iso_url

    @property
    def title(self):
        if self.operator is not None and self.operator != "":
            return self.operator
        else:
            return self.username

    def _hash_file(self, fname):
        """
        Calculates an md5sum of the passed in file (absolute path).

        Based on http://stackoverflow.com/a/4213255/84732
        """
        md5 = hashlib.md5()

        with open(fname, 'rb') as f:
            for chunk in iter(lambda: f.read(128), b''):
                md5.update(chunk)

        return md5.hexdigest()

    def on_complete(self):
        """
        sync calls here to trigger any completion tasks.

        - write or remove complete.txt
        - generate/update md5 files (removed on not-complete)
        - link/unlink via bindfs to archive dir
        """
        # Save a file called "completed.txt"
        completed_file = os.path.join(self.deployment_dir, "completed.txt")
        if self.completed is True:
            with open(completed_file, 'w') as f:
                f.write(" ")
        else:
            if os.path.exists(completed_file):
                os.remove(completed_file)

        # generate md5s of all data files on completion
        if self.completed:
            for dirpath, dirnames, filenames in os.walk(self.deployment_dir):
                for f in filenames:
                    if f in ["deployment.json", "wmoid.txt", "completed.txt"] or f.endswith(".md5"):
                        continue

                    full_file = os.path.join(dirpath, f)
                    md5_file = full_file + ".md5"

                    # only calc md5 if it does not exist, this is expensive!
                    if os.path.exists(md5_file):
                        continue

                    md5_value = self._hash_file(full_file)

                    md5_file = full_file + ".md5"
                    with open(md5_file, 'w') as mf:
                        mf.write(md5_value)
        else:
            for dirpath, dirnames, filenames in os.walk(self.deployment_dir):
                for f in filenames:
                    if f.endswith(".md5"):
                        os.unlink(os.path.join(dirpath, f))

        # link to archive user's ftp dir
        # this will only work on production
        if self.completed:
            try:
                archive_path = app.config.get('ARCHIVE_PATH')

                _, mname = os.path.split(self.deployment_dir)
                archive_mdir = os.path.join(archive_path, mname)
                if not os.path.exists(archive_mdir):
                    os.makedirs(archive_mdir)

                # local test
                #os.symlink(self.deployment_dir, archive_mdir)

                not_mounted = subprocess.call(['mountpoint', '-q', archive_mdir])
                if not_mounted == 1:
                    subprocess.call(['/usr/local/bin/bindfs', '-r', self.deployment_dir, archive_mdir])

            except Exception as e:
                warnings.warn("Could not link %s to %s: %s" % (self.deployment_dir, archive_mdir, e))
        else:
            try:

                archive_path = app.config.get('ARCHIVE_PATH')

                _, mname = os.path.split(self.deployment_dir)
                archive_mdir = os.path.join(archive_path, mname)

                if os.path.exists(archive_mdir):
                    not_mounted = subprocess.call(['mountpoint', '-q', archive_mdir])
                    if not_mounted == 0:
                        subprocess.call(['/usr/local/bin/bindfs', '-r', self.deployment_dir, archive_mdir])

            except Exception as e:
                warnings.warn("Could not unlink %s: %s" % (archive_mdir, e))

    def sync(self):
        if not os.path.exists(self.deployment_dir):
            try:
                os.makedirs(self.deployment_dir)
            except OSError:
                pass

        # Keep the WMO file updated if it is edited via the web form
        if self.wmo_id is not None and self.wmo_id != "":
            wmo_id_file = os.path.join(self.deployment_dir, "wmoid.txt")
            with open(wmo_id_file, 'w') as f:
                f.write(self.wmo_id)

        # trigger any completed tasks if necessary
        self.on_complete()

        # Serialize Deployment model to disk
        json_file = os.path.join(self.deployment_dir, "deployment.json")
        with open(json_file, 'w') as f:
            f.write(self.to_json())

    @classmethod
    def get_deployment_count_by_operator(cls):
        return db.deployments.aggregate({ '$group': { '_id': '$operator', 'count': { '$sum' : 1 }}}).get('result',[])

