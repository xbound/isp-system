# Generated by Django 2.0.5 on 2018-06-05 14:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webcom', '0002_auto_20180605_1414'),
    ]

    operations = [
        migrations.AlterField(
            model_name='service',
            name='included',
            field=models.ManyToManyField(blank=True, to='webcom.Service'),
        ),
    ]
