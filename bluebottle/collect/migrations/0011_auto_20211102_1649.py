# Generated by Django 2.2.24 on 2021-11-02 15:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collect', '0010_auto_20211102_1258'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collecttypetranslation',
            name='unit',
            field=models.CharField(blank=True, max_length=100, verbose_name='unit'),
        ),
        migrations.AlterField(
            model_name='collecttypetranslation',
            name='unit_plural',
            field=models.CharField(blank=True, max_length=100, verbose_name='unit_plural'),
        ),
    ]
