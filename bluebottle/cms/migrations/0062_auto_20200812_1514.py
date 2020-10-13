# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2020-07-17 08:37
from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations, models, connection
from django.utils.translation import activate, _trans
from tenant_extras.middleware import tenant_translation
from parler.models import TranslatableModelMixin


def remove_old_statistic_block_from_homepage(apps, schema_editor):
    StatsContent = apps.get_model('cms', 'StatsContent')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    for stats_content in StatsContent.objects.all():
        if stats_content.placeholder and stats_content.placeholder.parent_type.model == 'homepage':
            stats_content.stats.all().delete()
            with connection.cursor() as c:
                c.execute(
                    'delete from contentitem_cms_statscontent where contentitem_ptr_id = {};'.format(
                        stats_content.contentitem_ptr_id
                    )
                )


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0061_auto_20200812_1030'),
    ]

    operations = [
        migrations.RunPython(
            remove_old_statistic_block_from_homepage,
            migrations.RunPython.noop
        )
    ]
