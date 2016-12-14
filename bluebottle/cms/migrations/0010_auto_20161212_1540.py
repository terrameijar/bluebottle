# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-12-12 14:40
from __future__ import unicode_literals
import datetime

from django.db import migrations
from django.conf import settings


STATS = (
    ('people_involved', {'en': {'title': 'participants'}, 'nl': {'title': 'deelnemers'}}),
    ('projects_realized', {'en': {'title': 'projects realised'}, 'nl': {'title': 'project gerealiseerd'}}),
    ('donated_total', {'en': {'title': 'crowdfunded'}, 'nl': {'title': 'gegrowdfund'}}),
    ('tasks_realized', {'en': {'title': 'tasks'}, 'nl': {'title': 'taken'}}),
    ('votes_cast', {'en': {'title': 'votes cast'}, 'nl': {'title': 'stemmen'}})
)


PAGE = {
    'en': {
        'title': 'Let\'s make an impact together',
        'description': 'This is our impact in 2016',
        'slug': 'this-is-our-impact-in-2016'
    },
    'nl': {
        'title': 'Laten we samen impact maken',
        'description': 'Dit is onze impact in 2016',
        'slug': 'dit-is-onze-impact-in-2016'
    }
}


def create_default_result_pages(apps, schema_editor):
    languages = [lang[0] for lang in settings.LANGUAGES]

    Placeholder = apps.get_model('fluent_contents', 'Placeholder')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    ResultPage = apps.get_model('cms', 'ResultPage')
    StatsContent = apps.get_model('cms', 'StatsContent')
    Stats = apps.get_model('cms', 'Stats')
    Stat = apps.get_model('cms', 'Stat')
    ProjectsContent = apps.get_model('cms', 'ProjectsContent')
    Project = apps.get_model('projects', 'Project')
    Projects = apps.get_model('cms', 'Projects')
    ProjectImagesContent = apps.get_model('cms', 'ProjectImagesContent')
    ShareResultsContent = apps.get_model('cms', 'ShareResultsContent')
    ProjectsMapContent = apps.get_model('cms', 'ProjectsMapContent')

    # Create the page
    page = ResultPage.objects.create(
        start_date=datetime.date(2016, 1, 1),
        end_date=datetime.date(2017, 12, 31)
    )
    # And all the translations
    for language_code, attrs in PAGE.items():
        if language_code in languages:
            page.translations.create(
                language_code=language_code,
                **attrs
            )

    # Create the placeholder
    page_type = ContentType.objects.get_for_model(page)
    placeholder = Placeholder(
        parent_id=page.pk, parent_type_id=page_type.pk, slot='content', role='m'
    )
    placeholder.parent = page
    placeholder.save()

    # Create the stats list
    stats = Stats.objects.create()
    for type, translations in STATS:
        stat = Stat.objects.create(type=type, stats=stats)
        for language_code, attrs in translations.items():
            stat.translations.create(language_code=language_code, **attrs)

    # And the projects list
    projects = Projects.objects.create()
    for project in Project.objects.filter(
            status__slug='done-complete', campaign_ended__range=(page.start_date, page.end_date))[:3]:
        projects.projects.add(project)

    # All the content
    all_content = {
        StatsContent: {
            'en': {
                'stats': stats,
                'sort_order': 1
            },
            'nl': {
                'stats': stats,
                'sort_order': 1
            }

        },
        ProjectsContent: {
            'en': {
                'sort_order': 2,
                'title': "Projects that make us proud",
                'sub_title': "These projects made a big impact",
                'projects': projects
            },
            'nl': {
                'sort_order': 2,
                'title': "Projecten waar we trots op zijn",
                'sub_title': "Deze projecten maakten een grote impact",
                'projects': projects
            }
        },
        ProjectImagesContent: {
            'en': {
                'sort_order': 3,
                'description': "Join our community and let's make an impact together",
            },
            'nl': {
                'sort_order': 3,
                'description': "Word lid van onze community en laten we samen impact maken",
            }
        },
        ShareResultsContent: {
            'en': {
                'sort_order': 4,
                'title': "Share the impact!",
                'share_text': "Together with {people} people, we realised {tasks} tasks in {hours} hours"
            },
            'nl': {
                'sort_order': 4,
                'title': "Deel de impact!",
                'share_text': "Samen met {people} people, hebben we {tasks} taken gerealiseserd in {hours} uren"
            }
        },
        ProjectsMapContent: {
            'en': {
                'sort_order': 5,
                'title': 'We worked in these locations'
            },
            'nl': {
                'sort_order': 5,
                'title': 'We werkten in deze locaties'
            }
        }
    }

    def create_content_block(cls, content):
        content_type = ContentType.objects.get_for_model(cls)
        for language_code, attrs in content.items():
            if language_code in languages:
                cls.objects.create_for_placeholder(
                    placeholder,
                    language_code=language_code,
                    polymorphic_ctype=content_type,  # This does not get set automatically in migrations
                    **attrs
                )

    # create all the content
    for cls, content in all_content.items():
        create_content_block(cls, content)


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0009_merge_20161213_1047'),
    ]

    operations = [
        migrations.RunPython(create_default_result_pages)
    ]
