# Generated by Django 3.1.2 on 2020-10-22 12:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('release', '0004_auto_20200920_0150'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='symbol',
            name='meet',
        ),
    ]
