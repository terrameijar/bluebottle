# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-07-11 08:42
from __future__ import unicode_literals

from django.db import migrations, connection
from django.utils import timezone

from bluebottle.clients.utils import LocalTenant
from bluebottle.clients import properties


def create_terms(apps, schema_editor):
    Client = apps.get_model('clients', 'Client')
    Page = apps.get_model('pages', 'Page')
    Terms = apps.get_model('terms', 'Terms')
    Member = apps.get_model('members', 'Member')

    tenant = Client.objects.get(schema_name=connection.tenant.schema_name)
    properties.set_tenant(tenant)

    if properties.CLOSED_SITE:
        import ipdb; ipdb.set_trace()
        try:
            page = Page.objects.filter(slug='terms-and-conditions').first()
        except Page.DoesNotExist:
            try:
                page = Page.objects.get(slug='service')
            except Page.DoesNotExist:
                return

        terms = Terms.objects.filter(
            date__lte=timezone.now()
        ).order_by('-date').first()

        if terms:
            terms.page = page
            terms.save()
        else:
            Terms.objects.create(
                page=page,
                date=timezone.now(),
                version='1.0',
                author=Member.objects.get(email='admin@example.com')
            )


class Migration(migrations.Migration):

    dependencies = [
        ('terms', '0002_auto_20180711_0946'),
    ]

    operations = [
        migrations.RunPython(create_terms)
    ]
