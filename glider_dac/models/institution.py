#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
glider_dac/models/institution.py
Model definition for Institution
'''
from datetime import datetime
from glider_dac.extensions import db


class Institution(db.Model):
    institution_id = db.Column(db.String(255), primary_key=True)
    name = db.Column(db.String(255), unique=True)
    created = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated = db.Column(db.DateTime(timezone=True))
