# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-09-09 12:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0003_auto_20190909_1355'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignment',
            name='is_online',
            field=models.NullBooleanField(default=None),
        ),
    ]
