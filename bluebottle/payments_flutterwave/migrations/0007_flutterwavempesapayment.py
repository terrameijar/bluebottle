# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-05-02 07:48
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0003_auto_20161025_1221'),
        ('payments_flutterwave', '0006_auto_20170323_1227'),
    ]

    operations = [
        migrations.CreateModel(
            name='FlutterwaveMpesaPayment',
            fields=[
                ('payment_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='payments.Payment')),
                ('amount', models.CharField(blank=True, help_text=b'Amount / Transaction amount', max_length=200, null=True)),
                ('currency', models.CharField(blank=True, default=b'KES', help_text=b'Transaction currency', max_length=200, null=True)),
                ('business_number', models.CharField(blank=True, help_text=b'Amount', max_length=200, null=True)),
                ('account_number', models.CharField(blank=True, help_text=b'Billrefnumber / Account number', max_length=200, null=True)),
                ('kyc_info', models.TextField(blank=True, help_text=b'Personal details', null=True)),
                ('remote_id', models.CharField(blank=True, help_text=b'Remote id', max_length=200, null=True)),
                ('msisdn', models.CharField(blank=True, help_text=b'Msisdn / Phone number', max_length=200, null=True)),
                ('third_party_transaction_id', models.CharField(blank=True, help_text=b'Third party transaction id', max_length=200, null=True)),
                ('transaction_time', models.CharField(blank=True, help_text=b'Transaction time', max_length=200, null=True)),
                ('transaction_reference', models.CharField(blank=True, help_text=b'Flutterwave transaction reference', max_length=200, null=True)),
                ('invoice_number', models.CharField(blank=True, help_text=b'Invoice Number', max_length=200, null=True)),
                ('response', models.TextField(blank=True, help_text='Response from Flutterwave', null=True)),
                ('update_response', models.TextField(blank=True, help_text='Result from Flutterware (status update)', null=True)),
            ],
            options={
                'ordering': ('-created', '-updated'),
                'verbose_name': 'Flutterwave Mpesa Payment',
                'verbose_name_plural': 'Flutterwave Mpesa Payments',
            },
            bases=('payments.payment',),
        ),
    ]
