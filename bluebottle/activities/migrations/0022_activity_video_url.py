# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2020-05-20 12:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0021_auto_20200415_1501'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='video_url',
            field=models.URLField(blank=True, default=b'', help_text="Do you have a video pitch or a short movie that explains your activity? Cool! We can't wait to see it! You can paste the link to YouTube or Vimeo video here", max_length=100, null=True, verbose_name='video'),
        ),
    ]
