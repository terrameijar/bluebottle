# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-05-18 14:42
from __future__ import unicode_literals

import bluebottle.bb_projects.fields
import bluebottle.utils.utils
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import localflavor.generic.models
import sorl.thumbnail.fields
import taggit.managers


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('geo', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('utils', '__first__'),
        ('bb_projects', '0001_initial'),
        ('categories', '0001_initial'),
        ('taggit', '0002_auto_20150616_2121'),
        ('organizations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project_type', models.CharField(blank=True, choices=[(b'sourcing', 'Crowd-sourcing'), (b'funding', 'Crowd-funding'), (b'both', 'Crowd-funding & Crowd-sourcing')], max_length=50, null=True, verbose_name='Project type')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, help_text='When this project was created.', verbose_name='created')),
                ('updated', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='updated')),
                ('title', models.CharField(max_length=255, unique=True, verbose_name='title')),
                ('slug', models.SlugField(max_length=100, unique=True, verbose_name='slug')),
                ('pitch', models.TextField(blank=True, help_text='Pitch your smart idea in one sentence', verbose_name='pitch')),
                ('favorite', models.BooleanField(default=True)),
                ('deadline', models.DateTimeField(blank=True, null=True, verbose_name='deadline')),
                ('place', models.CharField(blank=True, help_text='Geographical location', max_length=100, null=True)),
                ('description', models.TextField(blank=True, help_text='Blow us away with the details!', verbose_name='why, what and how')),
                ('image', sorl.thumbnail.fields.ImageField(blank=True, help_text='Main project picture', max_length=255, upload_to=b'project_images/', verbose_name='image')),
                ('amount_asked', bluebottle.bb_projects.fields.MoneyField(blank=True, decimal_places=2, default=0, max_digits=12, null=True)),
                ('amount_donated', bluebottle.bb_projects.fields.MoneyField(decimal_places=2, default=0, max_digits=12)),
                ('amount_needed', bluebottle.bb_projects.fields.MoneyField(decimal_places=2, default=0, max_digits=12)),
                ('amount_extra', bluebottle.bb_projects.fields.MoneyField(blank=True, decimal_places=2, default=0, help_text='Amount pledged by organisation (matching fund).', max_digits=12, null=True)),
                ('account_holder_name', models.CharField(blank=True, max_length=255, null=True, verbose_name='account holder name')),
                ('account_holder_address', models.CharField(blank=True, max_length=255, null=True, verbose_name='account holder address')),
                ('account_holder_postal_code', models.CharField(blank=True, max_length=20, null=True, verbose_name='account holder postal code')),
                ('account_holder_city', models.CharField(blank=True, max_length=255, null=True, verbose_name='account holder city')),
                ('account_number', models.CharField(blank=True, max_length=255, null=True, verbose_name='Account number')),
                ('account_bic', localflavor.generic.models.BICField(blank=True, max_length=11, null=True, verbose_name='account SWIFT-BIC')),
                ('latitude', models.DecimalField(blank=True, decimal_places=18, max_digits=21, null=True, verbose_name='latitude')),
                ('longitude', models.DecimalField(blank=True, decimal_places=18, max_digits=21, null=True, verbose_name='longitude')),
                ('reach', models.PositiveIntegerField(blank=True, help_text='How many people do you expect to reach?', null=True, verbose_name='Reach')),
                ('video_url', models.URLField(blank=True, default=b'', help_text="Do you have a video pitch or a short movie that explains your project? Cool! We can't wait to see it! You can paste the link to YouTube or Vimeo video here", max_length=100, null=True, verbose_name='video')),
                ('popularity', models.FloatField(default=0)),
                ('is_campaign', models.BooleanField(default=False, help_text='Project is part of a campaign and gets special promotion.')),
                ('skip_monthly', models.BooleanField(default=False, help_text='Skip this project when running monthly donations', verbose_name='Skip monthly')),
                ('allow_overfunding', models.BooleanField(default=True)),
                ('story', models.TextField(blank=True, help_text='This is the help text for the story field', null=True, verbose_name='story')),
                ('effects', models.TextField(blank=True, help_text='What will be the Impact? How will your Smart Idea change the lives of people?', null=True, verbose_name='effects')),
                ('for_who', models.TextField(blank=True, help_text='Describe your target group', null=True, verbose_name='for who')),
                ('future', models.TextField(blank=True, help_text='How will this project be self-sufficient and sustainable in the long term?', null=True, verbose_name='future')),
                ('date_submitted', models.DateTimeField(blank=True, null=True, verbose_name='Campaign Submitted')),
                ('campaign_started', models.DateTimeField(blank=True, null=True, verbose_name='Campaign Started')),
                ('campaign_ended', models.DateTimeField(blank=True, null=True, verbose_name='Campaign Ended')),
                ('campaign_funded', models.DateTimeField(blank=True, null=True, verbose_name='Campaign Funded')),
                ('voting_deadline', models.DateTimeField(blank=True, null=True, verbose_name='Voting Deadline')),
                ('account_bank_country', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='project_account_bank_country', to='geo.Country')),
                ('account_holder_country', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='project_account_holder_country', to='geo.Country')),
                ('categories', models.ManyToManyField(blank=True, to='categories.Category')),
                ('country', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='geo.Country')),
                ('language', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='utils.Language')),
                ('location', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='geo.Location')),
                ('organization', models.ForeignKey(blank=True, help_text='Project organization', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='organization', to='organizations.Organization', verbose_name='organization')),
                ('owner', models.ForeignKey(help_text='Campaigner', on_delete=django.db.models.deletion.CASCADE, related_name='owner', to=settings.AUTH_USER_MODEL, verbose_name='campaigner')),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bb_projects.ProjectPhase')),
                ('tags', taggit.managers.TaggableManager(blank=True, help_text='Add tags', through='taggit.TaggedItem', to='taggit.Tag', verbose_name='tags')),
                ('theme', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='bb_projects.ProjectTheme')),
            ],
            options={
                'ordering': ['title'],
                'abstract': False,
                'verbose_name': 'campaign',
                'verbose_name_plural': 'projects',
            },
            bases=(models.Model, bluebottle.utils.utils.GetTweetMixin),
        ),
        migrations.CreateModel(
            name='ProjectBudgetLine',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(default=b'', max_length=255, verbose_name='description')),
                ('currency', models.CharField(default=b'EUR', max_length=3)),
                ('amount', models.PositiveIntegerField(verbose_name='amount (in cents)')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True)),
                ('updated', django_extensions.db.fields.ModificationDateTimeField(auto_now=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.Project')),
            ],
            options={
                'verbose_name': 'budget line',
                'verbose_name_plural': 'budget lines',
            },
        ),
        migrations.CreateModel(
            name='ProjectDocument',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=b'projects/documents')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('updated', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='updated')),
                ('deleted', models.DateTimeField(blank=True, null=True, verbose_name='deleted')),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='author')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='projects.Project')),
            ],
            options={
                'abstract': False,
                'verbose_name': 'project document',
                'verbose_name_plural': 'project documents',
            },
        ),
        migrations.CreateModel(
            name='ProjectPhaseLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, help_text='When this project entered in this status.', verbose_name='created')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.Project')),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bb_projects.ProjectPhase')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
