# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-12-07 14:39
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funding_telesom', '0004_auto_20200707_0929'),
    ]

    operations = [
        migrations.AlterField(
            model_name='telesompayment',
            name='currency',
            field=models.CharField(default='USD', max_length=50),
        ),
        migrations.AlterField(
            model_name='telesompayment',
            name='issuer_transaction_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='telesompayment',
            name='reference_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='telesompayment',
            name='response',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='telesompayment',
            name='transaction_amount',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='telesompayment',
            name='transaction_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='telesompayment',
            name='unique_id',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='telesompaymentprovider',
            name='api_url',
            field=models.CharField(default='https://sandbox.safarifoneict.com/asm/', max_length=100),
        ),
        migrations.AlterField(
            model_name='telesompaymentprovider',
            name='prefix',
            field=models.CharField(default='goodup', max_length=10),
        ),
    ]
