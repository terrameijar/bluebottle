# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-07-10 06:51
from __future__ import unicode_literals

import bluebottle.fsm
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0006_auto_20190605_1453'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='highlight',
            field=models.BooleanField(default=False, help_text='Highlight this activity to show it on homepage'),
        ),
    ]
