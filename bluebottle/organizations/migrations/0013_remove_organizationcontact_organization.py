# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-04-16 13:37
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0012_auto_20190416_1101'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='organizationcontact',
            name='organization',
        ),
    ]
