# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2021-03-03 07:32
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('initiatives', '0032_auto_20210303_0820'),
    ]

    operations = [
        migrations.RunSQL('alter sequence bb_projects_projecttheme_id_seq rename to initiatives_theme_id_seq;'),
        migrations.RunSQL('alter sequence bb_projects_projecttheme_translation_id_seq rename to initiatives_theme_translation_id_seq;'),
    ]
