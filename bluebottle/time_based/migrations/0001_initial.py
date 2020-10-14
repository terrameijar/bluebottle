# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-10-14 09:55
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('geo', '0017_auto_20201014_1155'),
        ('tasks', '0044_auto_20201014_1155'),
    ]

    operations = [
        migrations.CreateModel(
            name='TimeBasedActivity',
            fields=[
                ('activity_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='activities.Activity')),
                ('capacity', models.PositiveIntegerField(blank=True, null=True, verbose_name='attendee limit')),
                ('is_online', models.NullBooleanField(default=None, verbose_name='is online')),
                ('location_hint', models.TextField(blank=True, null=True, verbose_name='location hint')),
                ('registration_deadline', models.DateField(blank=True, null=True, verbose_name='deadline to apply')),
                ('review', models.NullBooleanField(default=None, verbose_name='review applications')),
            ],
            options={
                'abstract': False,
            },
            bases=('activities.activity',),
        ),
        migrations.CreateModel(
            name='OnADateActivity',
            fields=[
                ('timebasedactivity_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='time_based.TimeBasedActivity')),
                ('start', models.DateTimeField(blank=True, null=True, verbose_name='end date and time')),
                ('duration', models.FloatField(blank=True, null=True, verbose_name='duration')),
            ],
            options={
                'abstract': False,
            },
            bases=('time_based.timebasedactivity',),
        ),
        migrations.CreateModel(
            name='OngoingActivity',
            fields=[
                ('timebasedactivity_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='time_based.TimeBasedActivity')),
            ],
            options={
                'abstract': False,
            },
            bases=('time_based.timebasedactivity',),
        ),
        migrations.CreateModel(
            name='WithADeadlineActivity',
            fields=[
                ('timebasedactivity_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='time_based.TimeBasedActivity')),
                ('deadline', models.DateTimeField(blank=True, null=True, verbose_name='deadline')),
            ],
            options={
                'abstract': False,
            },
            bases=('time_based.timebasedactivity',),
        ),
        migrations.AddField(
            model_name='timebasedactivity',
            name='expertise',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='tasks.Skill', verbose_name='skill'),
        ),
        migrations.AddField(
            model_name='timebasedactivity',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='geo.Geolocation', verbose_name='location'),
        ),
    ]
