# Generated by Django 3.1.1 on 2020-09-10 12:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('convert', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='contact',
            name='phoneid',
        ),
    ]