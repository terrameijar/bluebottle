# Generated by Django 2.2.24 on 2021-11-19 10:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('collect', '0015_auto_20211109_1123'),
    ]

    operations = [
        migrations.RenameField(
            model_name='collectactivity',
            old_name='type',
            new_name='collect_type',
        ),
    ]
