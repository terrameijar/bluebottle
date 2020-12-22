# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-11-11 12:19
from __future__ import unicode_literals

from django.db import migrations
from bluebottle.utils.utils import update_group_permissions


def add_group_permissions(apps, schema_editor):
    group_perms = {
        'Staff': {
            'perms': (
                'change_donor',
            )
        },
    }

    update_group_permissions('funding', group_perms, apps)


class Migration(migrations.Migration):

    dependencies = [
        ('funding', '0061_auto_20201202_1044'),
    ]

    operations = [
        migrations.RunPython(add_group_permissions)
    ]
