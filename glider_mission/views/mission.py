import os
import os.path
from datetime import datetime
import json
import shutil

from flask import render_template, make_response, redirect, jsonify, flash, url_for, request
from flask_login import login_required, login_user, logout_user, current_user
from glider_mission import app, db, datetimeformat
from glider_mission.glider_emails import send_wmoid_email

from flask.ext.wtf import Form
from wtforms import TextField, SubmitField, BooleanField

class MissionForm(Form):
    estimated_deploy_date       = TextField(u'Estimated Deploy Date (yyyy-mm-dd)')
    estimated_deploy_location   = TextField(u'Estimated Deploy Location (WKT)')
    wmo_id                      = TextField(u'WMO ID')
    completed                   = BooleanField(u'Completed')
    submit                      = SubmitField(u'Submit')

class NewMissionForm(Form):
    name    = TextField(u'Mission Name')
    wmo_id  = TextField(u'WMO ID')
    submit  = SubmitField(u"Create")

@app.route('/users/<string:username>/missions')
def list_user_missions(username):
    user = db.User.find_one( {'username' : username } )
    missions = list(db.Mission.find( { 'user_id' : user._id } ))

    kwargs = {}
    if current_user and current_user.is_active() and (current_user.is_admin() or current_user == user):
        # Permission to edit
        form = NewMissionForm()
        kwargs['form'] = form

    for m in missions:
        if not os.path.exists(m.mission_dir):   # wat
            continue

        m.updated = datetime.fromtimestamp(os.path.getmtime(m.mission_dir))

    missions = sorted(missions, lambda a, b: cmp(b.updated, a.updated))

    return render_template('user_missions.html', username=username, missions=missions, **kwargs)

@app.route('/users/<string:username>/mission/<ObjectId:mission_id>')
def show_mission(username, mission_id):
    user = db.User.find_one( {'username' : username } )
    mission = db.Mission.find_one({'_id':mission_id})

    files = []
    for dirpath, dirnames, filenames in os.walk(mission.mission_dir):
        for f in filenames:
            if f in ["wmoid.txt", "completed.txt"]:
                continue
            files.append((f, datetime.fromtimestamp(os.path.getmtime(os.path.join(dirpath, f)))))

    files = sorted(files, lambda a,b: cmp(b[1], a[1]))

    kwargs = {}

    form = MissionForm(obj=mission)

    if current_user and current_user.is_active() and (current_user.is_admin() or current_user == user):
        kwargs['editable'] = True
        if current_user.is_admin():
            kwargs['admin'] = True

    return render_template('show_mission.html', username=username, form=form, mission=mission, files=files, **kwargs)

@app.route('/mission/<ObjectId:mission_id>')
def show_mission_no_username(mission_id):
    mission = db.Mission.find_one( { '_id' : mission_id } )
    username = db.User.find_one( { '_id' : mission.user_id } ).username
    return redirect(url_for('show_mission', username=username, mission_id=mission._id))

@app.route('/users/<string:username>/mission/new', methods=['POST'])
@login_required
def new_mission(username):
    user = db.User.find_one( {'username' : username } )
    if user is None or (user is not None and not current_user.is_admin() and current_user != user):
        # No permission
        flash("Permission denied", 'danger')
        return redirect(url_for("index"))

    form = NewMissionForm()

    if form.validate_on_submit():

        upload_root = os.path.join(user.data_root, 'upload')
        new_mission_dir = os.path.join(upload_root, form.name.data)

        mission = db.Mission()
        form.populate_obj(mission)
        mission.user_id = user._id
        mission.mission_dir = new_mission_dir
        mission.updated = datetime.utcnow()
        mission.save()
        mission.sync()
        flash("Mission created", 'success')

        if not mission.wmo_id:
            send_wmoid_email(username, mission)

    return redirect(url_for('list_user_missions', username=username))


@app.route('/users/<string:username>/mission/<ObjectId:mission_id>/edit', methods=['POST'])
@login_required
def edit_mission(username, mission_id):

    user = db.User.find_one( {'username' : username } )
    if user is None or (user is not None and not current_user.is_admin() and current_user != user):
        # No permission
        flash("Permission denied", 'danger')
        return redirect(url_for('list_user_missions', username=username))

    mission = db.Mission.find_one({'_id':mission_id})

    form = MissionForm(obj=mission)

    if form.validate_on_submit():
        form.populate_obj(mission)
        mission.updated = datetime.utcnow()
        try:
            mission.estimated_deploy_date = datetime.strptime(form.estimated_deploy_date.data, "%Y-%m-%d")
        except ValueError:
            mission.estimated_deploy_date = None
        mission.save()
        mission.sync()
        flash("Mission updated", 'success')
        return redirect(url_for('show_mission', username=username, mission_id=mission._id))

    return render_template('edit_mission.html', username=username, form=form, mission=mission)

@app.route('/users/<string:username>/mission/<ObjectId:mission_id>/files', methods=['POST'])
@login_required
def post_mission_file(username, mission_id):

    mission = db.Mission.find_one({'_id':mission_id})
    user = db.User.find_one( {'username' : username } )

    if not (mission and user and mission.user_id == user._id and (current_user.is_admin() or current_user == user)):
        raise StandardError("Unauthorized") # @TODO better response via ajax?

    retval = []
    for name, f in request.files.iteritems():
        if not name.startswith('file-'):
            continue

        safe_filename = f.filename # @TODO

        out_name = os.path.join(mission.mission_dir, safe_filename)

        with open(out_name, 'w') as of:
            f.save(of)

        retval.append((safe_filename, datetimeformat(datetime.now())))

    editable = current_user and current_user.is_active() and (current_user.is_admin() or current_user == user)

    return render_template("_mission_files.html", files=retval, editable=editable)

@app.route('/users/<string:username>/mission/<ObjectId:mission_id>/delete_files', methods=['POST'])
@login_required
def delete_mission_files(username, mission_id):

    mission = db.Mission.find_one({'_id':mission_id})
    user = db.User.find_one({'username':username})

    if not (mission and user and (current_user.is_admin() or user._id == mission.user_id)):
            raise StandardError("Unauthorized")     # @TODO better response via ajax?

    for name in request.json['files']:
        file_name = os.path.join(mission.mission_dir, name)
        os.unlink(file_name)

    return ""

@app.route('/users/<string:username>/mission/<ObjectId:mission_id>/delete', methods=['POST'])
@login_required
def delete_mission(username, mission_id):

    mission = db.Mission.find_one({'_id':mission_id})
    user = db.User.find_one( {'username' : username } )

    if not (mission is not None and user is not None and mission.user_id == user._id and current_user.is_admin()):
        flash("Permission denied", 'danger')
        return redirect(url_for("show_mission", username=username, mission_id=mission_id))

    shutil.rmtree(mission.mission_dir)
    mission.delete()

    return redirect(url_for("list_user_missions", username=username))
