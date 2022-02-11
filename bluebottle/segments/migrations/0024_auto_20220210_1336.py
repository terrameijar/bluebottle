# Generated by Django 2.2.24 on 2022-02-10 12:36

import bluebottle.utils.fields
import bluebottle.utils.validators
import colorfield.fields
from django.db import migrations, models
import django_better_admin_arrayfield.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('segments', '0023_auto_20220209_1312'),
    ]

    operations = [
        migrations.AddField(
            model_name='segmenttype',
            name='inherit',
            field=models.BooleanField(default=True, help_text='Newly created activities will inherit the segments set on the activity owner.', verbose_name='Inherit'),
        ),
        migrations.AlterField(
            model_name='segment',
            name='alternate_names',
            field=django_better_admin_arrayfield.models.fields.ArrayField(base_field=models.CharField(max_length=200), blank=True, default=list, size=None),
        ),
        migrations.AlterField(
            model_name='segment',
            name='background_color',
            field=colorfield.fields.ColorField(blank=True, default=None, help_text='Add a background colour to your segment page.', max_length=18, null=True, verbose_name='Background color'),
        ),
        migrations.AlterField(
            model_name='segment',
            name='closed',
            field=models.BooleanField(default=False, help_text='Closed segments will only be accessible to members that belong to this segment.', verbose_name='Restricted'),
        ),
        migrations.AlterField(
            model_name='segment',
            name='cover_image',
            field=bluebottle.utils.fields.ImageField(blank=True, help_text='The uploaded image will be cropped to fit a 4:3 rectangle.', max_length=255, null=True, upload_to='categories/logos/', validators=[bluebottle.utils.validators.FileMimetypeValidator(['image/png', 'image/jpeg', 'image/gif', 'image/svg+xml'], None, 'invalid_mimetype'), bluebottle.utils.validators.validate_file_infection], verbose_name='cover image'),
        ),
        migrations.AlterField(
            model_name='segment',
            name='email_domains',
            field=django_better_admin_arrayfield.models.fields.ArrayField(base_field=models.CharField(max_length=200), blank=True, default=list, help_text='Users with email addresses for this domain are automatically added to this segment.', size=None, verbose_name='Email domains'),
        ),
        migrations.AlterField(
            model_name='segment',
            name='logo',
            field=bluebottle.utils.fields.ImageField(blank=True, help_text='The uploaded image will be scaled so that it is fully visible.', max_length=255, null=True, upload_to='categories/logos/', validators=[bluebottle.utils.validators.FileMimetypeValidator(['image/png', 'image/jpeg', 'image/gif', 'image/svg+xml'], None, 'invalid_mimetype'), bluebottle.utils.validators.validate_file_infection], verbose_name='logo'),
        ),
        migrations.AlterField(
            model_name='segment',
            name='story',
            field=models.TextField(blank=True, help_text='A more detailed story for your segment. This story can be accessed via a link on the page.', null=True, verbose_name='Story'),
        ),
        migrations.AlterField(
            model_name='segment',
            name='tag_line',
            field=models.CharField(blank=True, help_text='A short sentence to explain your segment. This sentence is directly visible on the page.', max_length=255, null=True, verbose_name='Slogan'),
        ),
        migrations.AlterField(
            model_name='segmenttype',
            name='enable_search',
            field=models.BooleanField(default=False, verbose_name='Enable search filters'),
        ),
    ]
