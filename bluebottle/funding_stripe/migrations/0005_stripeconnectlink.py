# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2020-09-08 12:47
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('funding_stripe', '0004_auto_20200318_1504'),
    ]

    operations = [
        migrations.CreateModel(
            name='StripeConnectLink',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('link', models.CharField(max_length=255)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='funding_stripe.StripePayoutAccount')),
            ],
        ),
    ]
