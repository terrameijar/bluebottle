# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-07-03 13:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funding_flutterwave', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='flutterwavepaymentprovider',
            name='prefix',
            field=models.CharField(default=b'goodup', max_length=100),
        ),
    ]
