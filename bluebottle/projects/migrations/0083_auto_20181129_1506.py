# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-11-29 14:06
from __future__ import unicode_literals

from django.db import migrations


def migrate_payout_details(apps, schema_editor):

    Project = apps.get_model('projects', 'Project')
    PlainPayoutAccount = apps.get_model('payouts', 'PlainPayoutAccount')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    new_ct = ContentType.objects.get_for_model(PlainPayoutAccount)

    for project in Project.objects.all():
        project.payout_account = PlainPayoutAccount.objects.create(
            user=project.owner,
            account_holder_name=project.account_holder_name,
            account_holder_address=project.account_holder_address,
            account_holder_postal_code=project.account_holder_postal_code,
            account_holder_city=project.account_holder_city,
            account_holder_country=project.account_holder_country,
            account_number=project.account_number,
            account_details=project.account_details,
            account_bank_country=project.account_bank_country,
            polymorphic_ctype=new_ct
        )
        project.save()

        if len(project.documents):
            document = project.documents.all()[0]
            project.payout_account.document = PayoutDocument(
                author=document.document,
                file=document.file,
                created=document.created,
                updated=document.updated,
                ip_address=document.ip_address
            )
            project_payout.save()


def remove_payout_accounts(apps, schema_editor):
    PlainPayoutAccount = apps.get_model('payouts', 'PlainPayoutAccount')
    PlainPayoutAccount.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0082_auto_20181129_1506'),
        ('payouts', '0008_auto_20181129_1451')
    ]

    operations = [
        migrations.RunPython(migrate_payout_details, remove_payout_accounts)
    ]
