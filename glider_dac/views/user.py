#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
glider_dac/views/user.py
View definitions for Users
'''
from flask import (render_template, redirect, flash, url_for, request,
                   Blueprint, current_app)
from flask_login import login_required, current_user
#from glider_dac import app, db
from glider_dac import db
from glider_dac.models.user import User
from flask_wtf import FlaskForm
from wtforms import validators, StringField, PasswordField, SubmitField
from wtforms.form import BaseForm


class UserForm(FlaskForm):
    username = StringField('Username')
    name = StringField('Name')
    password = PasswordField('Password', [
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Confirm Password')
    organization = StringField('Organization')
    email = StringField('Email')
    submit = SubmitField("Submit")


user_bp = Blueprint("user", __name__)


@user_bp.route('/users/<string:username>', methods=['GET', 'POST'])
@login_required
def edit_user(username):
    current_app.logger.info("GET %s", username)
    current_app.logger.info("Request URL: %s", request.url)
    user = User.query.filter_by(username=username).one_or_none()
    if user is None or (user is not None and not current_user.is_admin and
                        current_user != user):
        # No permission
        current_app.logger.error("Permission is denied")
        current_app.logger.error("User: %s", user)
        current_app.logger.error("Admin?: %s", current_user.is_admin)
        current_app.logger.error("Not current user?: %s", current_user != user)
        flash("Permission denied", 'danger')
        return redirect(url_for("index"))

    form = UserForm(obj=user)

    if form.validate_on_submit():
        form.populate_obj(user)
        user.save()
        if form.password.data:
            User.update(username=user.username, password=form.password.data)
        flash("Account updated", 'success')
        return redirect(url_for("index"))

    return render_template('edit_user.html', form=form, user=user)


@user_bp.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin:
        # No permission
        flash("Permission denied", 'danger')
        return redirect(url_for("index"))

    form = UserForm()

    if (form.is_submitted() and
        BaseForm.validate(form,
                          extra_validators={'password':
                                            [validators.InputRequired()]})):
        user = User()
        form.populate_obj(user)
        user.save()
        User.update(username=user.username, password=form.password.data)
        db.session.add(user)
        db.session.commit()

        flash("Account for '%s' created" % user.username, 'success')
        return redirect(url_for("admin"))

    users = User.query.all()

    subquery = db.session.query(
        Deployment.user_id,
        func.count().label('deployments_count')
    ).group_by(Deployment.user_id).subquery()

    # Query to join User table with the subquery
    user_deployment_counts= db.session.query(
        User.username,
        User.name,
        User.email,
        User.organization,
        subquery.c.deployments_count
    ).join(subquery, subquery.c.user_id == User.user_id).all()

    current_app.logger.info(user_deployment_counts[0])

    return render_template('admin.html', form=form,
                           deployment_counts=user_deployment_counts)


# TODO: Merge with regular admin editing page
@user_bp.route('/admin/<string:username>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if not current_user.is_admin:
        # No permission
        flash("Permission denied", 'danger')
        return redirect(url_for("index"))

    user = User.query.filter_by(username=username).one_or_none()

    form = UserForm(obj=user)

    if form.validate_on_submit():
        form.populate_obj(user)
        # TODO: update application
        user.save()
        if form.password.data:
            User.update(username=user.username, password=form.password.data)
        flash("Account updated", 'success')
        return redirect(url_for("admin"))

    return render_template('edit_user.html', form=form, user=user)


@user_bp.route('/admin/<string:username>/delete', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        # No permission
        flash("Permission denied", 'danger')
        return redirect(url_for("index"))

    user = User.query.filter_by(username=username).one_or_none()

    if user._id == current_user._id:
        flash("You can't delete yourself!", "danger")
        return redirect(url_for("admin"))

    # TODO: is this a valid SQLAlchemy method?
    user.delete()

    flash("User deleted", "success")
    return redirect(url_for('admin'))
