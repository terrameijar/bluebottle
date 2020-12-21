# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-10-29 11:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('time_based', '0016_auto_20201028_1550'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='duration',
            name='period',
        ),
        migrations.AddField(
            model_name='duration',
            name='period_duration',
            field=models.DurationField(blank=True, null=True, verbose_name='duration'),
        ),
        migrations.AddField(
            model_name='duration',
            name='start',
            field=models.DateField(blank=True, null=True, verbose_name='start'),
        ),
        migrations.AlterField(
            model_name='duration',
            name='value',
            field=models.DurationField(blank=True, null=True, verbose_name='value'),
        ),
    ]
