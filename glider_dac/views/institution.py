#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
glider_dac/views/institution.py
View definition for institutions
'''

from flask import (current_app, render_template, redirect, flash, url_for,
                   jsonify, request, Blueprint)
from flask_cors import cross_origin
from flask_login import current_user
#from glider_dac import app, db
from glider_dac import db
from glider_dac.models.institution import Institution
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from functools import wraps
import json


institution_bp = Blueprint("institution", __name__)

def error_wrapper(func):
    '''
    Function wrapper to catch exceptions and return them as jsonified errors
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return jsonify(error=type(e).__name__, message=e.message), 500
    return wrapper


def admin_required(func):
    '''
    Wraps a route to require an administrator
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_app.login_manager._login_disabled:
            return func(*args, **kwargs)
        elif not current_user.is_authenticated:
            return app.login_manager.unauthorized()
        elif not current_user.admin:
            flash("Permission denied", 'danger')
            return redirect(url_for('index.index'))
        return func(*args, **kwargs)
    return wrapper


class NewInstitutionForm(FlaskForm):
    name = StringField('Institution Name')
    submit = SubmitField('New Institution')


@institution_bp.route('/institutions/', methods=['GET', 'POST'])
@admin_required
def show_institutions():
    institutions = Institution.query.all()
    form = NewInstitutionForm()
    if form.validate_on_submit():
        institution = Institution()
        institution.name = form.name.data
        institution.save()
        db.session.add(institution)
        db.session.commit()
        flash('Institution Created', 'success')

    return render_template('institutions.html',
                           form=form,
                           institutions=institutions)


@institution_bp.route('/api/institution', methods=['GET'])
@cross_origin()
def get_institutions():
    institutions = [json.loads(inst.to_json()) for inst in Institution.query.all()]
    return jsonify(results=institutions)


@institution_bp.route('/api/institution', methods=['POST'])
@admin_required
@error_wrapper
def new_institution():
    current_app.logger.info(request.data)
    data = json.loads(request.data)
    institution = Institution()
    institution.name = data['name']
    institution.save()
    db.session.add(institution)
    db.session.commit()
    return institution.to_json()


@institution_bp.route('/api/institution/<string:institution_id>',
                      methods=['DELETE'])
@admin_required
@error_wrapper
def delete_institution(institution_id):
    if not current_user.admin:
        flash("Permission denied", 'danger')
        return redirect(url_for('index.index'))
    institution = Institution.query.filter_by(institution_id=institution_id).one_or_none()
    if institution is None:
        return jsonify({}), 404
    current_app.logger.info(f"Deleting institution {institution.name}")
    db.session.delete(institution)
    db.session.commit()
    return jsonify({}), 204
