# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-02-24 14:08
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0039_auto_20210218_1111'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='OrganizerContribution',
            new_name='EffortContribution',
        ),
        migrations.AlterModelOptions(
            name='effortcontribution',
            options={'verbose_name': 'Effort', 'verbose_name_plural': 'Contributions'},
        ),
    ]
