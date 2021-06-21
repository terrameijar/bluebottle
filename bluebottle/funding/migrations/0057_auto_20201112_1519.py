# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-11-12 14:19
from __future__ import unicode_literals

import bluebottle.files.fields
import bluebottle.utils.fields
from django.db import migrations, models
import django.db.models.deletion
import djmoney.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('funding', '0056_auto_20201112_1509'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bankaccount',
            options={'ordering': ('id',)},
        ),
        migrations.AlterModelOptions(
            name='plainpayoutaccount',
            options={'verbose_name': 'Plain KYC account', 'verbose_name_plural': 'Plain KYC accounts'},
        ),
        migrations.RenameField(
            model_name='donation',
            old_name='contribution_ptr',
            new_name='contributor_ptr',
        ),
        migrations.AlterField(
            model_name='budgetline',
            name='amount',
            field=bluebottle.utils.fields.MoneyField(currency_choices=[('EUR', 'Euro')], decimal_places=2, default_currency='EUR', max_digits=12),
        ),
        migrations.AlterField(
            model_name='budgetline',
            name='amount_currency',
            field=djmoney.models.fields.CurrencyField(choices=[('EUR', 'Euro')], default='EUR', editable=False, max_length=50),
        ),
        migrations.AlterField(
            model_name='budgetline',
            name='description',
            field=models.CharField(default='', max_length=255, verbose_name='description'),
        ),
        migrations.AlterField(
            model_name='donation',
            name='amount',
            field=bluebottle.utils.fields.MoneyField(currency_choices=[('EUR', 'Euro')], decimal_places=2, default_currency='EUR', max_digits=12),
        ),
        migrations.AlterField(
            model_name='donation',
            name='amount_currency',
            field=djmoney.models.fields.CurrencyField(choices=[('EUR', 'Euro')], default='EUR', editable=False, max_length=50),
        ),
        migrations.AlterField(
            model_name='donation',
            name='payout_amount',
            field=bluebottle.utils.fields.MoneyField(currency_choices=[('EUR', 'Euro')], decimal_places=2, default_currency='EUR', max_digits=12),
        ),
        migrations.AlterField(
            model_name='funding',
            name='target_currency',
            field=djmoney.models.fields.CurrencyField(choices=[('EUR', 'Euro')], default='EUR', editable=False, max_length=50),
        ),
        migrations.AlterField(
            model_name='fundraiser',
            name='amount',
            field=bluebottle.utils.fields.MoneyField(currency_choices=[('EUR', 'Euro')], decimal_places=2, default_currency='EUR', max_digits=12, verbose_name='amount'),
        ),
        migrations.AlterField(
            model_name='fundraiser',
            name='amount_currency',
            field=djmoney.models.fields.CurrencyField(choices=[('EUR', 'Euro')], default='EUR', editable=False, max_length=50),
        ),
        migrations.AlterField(
            model_name='paymentcurrency',
            name='code',
            field=models.CharField(default='EUR', max_length=50),
        ),
        migrations.AlterField(
            model_name='plainpayoutaccount',
            name='document',
            field=bluebottle.files.fields.PrivateDocumentField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='files.PrivateDocument'),
        ),
        migrations.AlterField(
            model_name='reward',
            name='amount',
            field=bluebottle.utils.fields.MoneyField(currency_choices=[('EUR', 'Euro')], decimal_places=2, default_currency='EUR', max_digits=12, verbose_name='Amount'),
        ),
        migrations.AlterField(
            model_name='reward',
            name='amount_currency',
            field=djmoney.models.fields.CurrencyField(choices=[('EUR', 'Euro')], default='EUR', editable=False, max_length=50),
        ),
    ]
