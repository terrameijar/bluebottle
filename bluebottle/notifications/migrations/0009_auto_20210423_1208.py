# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2021-04-23 10:08
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0008_remove_notificationplatformsettings_match_options'),
    ]

    operations = [
        migrations.RenameField(
            model_name='notificationplatformsettings',
            old_name='_match_options',
            new_name='match_options',
        ),
    ]
