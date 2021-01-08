# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2021-01-06 14:09
from __future__ import unicode_literals

from django.db import migrations
from django.utils.timezone import now


def map_status(status):

    mapping = {
        'draft': 'draft',
        'submitted': 'draft',
        'needs_work': 'draft',
        'rejected': 'draft',
        'deleted': 'draft',
        'cancelled': 'draft',
        'expired': 'finished',
        'open': 'open',
        'succeeded': 'finished',
        'full': 'full',
        'running': 'running'

    }
    return getattr(mapping, status, 'draft')

def migrate_to_slots(apps, schema_editor):
    DateActivity = apps.get_model('time_based', 'DateActivity')
    DateActivitySlot = apps.get_model('time_based', 'DateActivitySlot')

    for activity in DateActivity.objects.all():
        status = map_status(activity.status)
        slot = DateActivitySlot(
            status=status,
            activity_id=activity.id,
            start=activity.start,
            duration=activity.duration,
            is_online=activity.is_online,
            online_meeting_url=activity.online_meeting_url,
            location=activity.location,
            location_hint=activity.location_hint
        )
        if slot.start and slot.duration and slot.start + slot.duration < now():
            slot.status = 'finished'

        if slot.status == 'draft' \
                and slot.start \
                and slot.duration \
                and (slot.is_online or slot.location):
            slot.status = 'open'

        slot.execute_triggers(send_messages=False)
        slot.save()


class Migration(migrations.Migration):

    dependencies = [
        ('time_based', '0046_auto_20210106_1507'),
    ]

    operations = [
        migrations.RunPython(
            migrate_to_slots,
            migrations.RunPython.noop
        )
    ]
