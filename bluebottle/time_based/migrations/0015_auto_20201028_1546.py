# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-10-28 14:46
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('time_based', '0014_auto_20201028_1544'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ContributionDuration',
            new_name='Duration',
        ),
    ]
