# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-05-22 11:41
from __future__ import unicode_literals

import bluebottle.geo.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('geo', '0011_activityplace'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activityplace',
            name='position',
            field=bluebottle.geo.fields.PointField(max_length=42),
        ),
    ]
