# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-08-10 20:09
from __future__ import unicode_literals

import bluebottle.utils.fields
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('projects', '0030_rename_account_bic_20170705_1221'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='promoter',
            field=models.ForeignKey(blank=True, help_text='Project Promoter', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='promoter', to=settings.AUTH_USER_MODEL, verbose_name='promoter'),
        ),
        migrations.AddField(
            model_name='project',
            name='task_manager',
            field=models.ForeignKey(blank=True, help_text='Project Task Manager', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='task_manager', to=settings.AUTH_USER_MODEL, verbose_name='task manager'),
        ),
    ]
