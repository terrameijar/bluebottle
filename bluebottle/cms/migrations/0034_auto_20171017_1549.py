# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2017-10-17 13:49
from __future__ import unicode_literals

import bluebottle.utils.fields
from django.db import migrations, models
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0033_auto_20171017_1353'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='slidetranslation',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='slidetranslation',
            name='master',
        ),
        migrations.AddField(
            model_name='slide',
            name='background_image',
            field=bluebottle.utils.fields.ImageField(blank=True, max_length=255, null=True, upload_to=b'banner_slides/', verbose_name='Background image'),
        ),
        migrations.AddField(
            model_name='slide',
            name='image',
            field=bluebottle.utils.fields.ImageField(blank=True, max_length=255, null=True, upload_to=b'banner_slides/', verbose_name='Image'),
        ),
        migrations.AddField(
            model_name='slide',
            name='link_text',
            field=models.CharField(blank=True, help_text='This is the text on the button inside the banner.', max_length=400, verbose_name='Link text'),
        ),
        migrations.AddField(
            model_name='slide',
            name='link_url',
            field=models.CharField(blank=True, help_text='This is the link for the button inside the banner.', max_length=400, verbose_name='Link url'),
        ),
        migrations.AddField(
            model_name='slide',
            name='tab_text',
            field=models.CharField(default='', help_text='This is shown on tabs beneath the banner.', max_length=100, verbose_name='Tab text'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='slide',
            name='video_url',
            field=models.URLField(blank=True, default=b'', max_length=100, verbose_name='Video url'),
        ),
        migrations.DeleteModel(
            name='SlideTranslation',
        ),
    ]
