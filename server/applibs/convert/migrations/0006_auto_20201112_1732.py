# Generated by Django 3.1.3 on 2020-11-12 09:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('convert', '0005_auto_20201103_0020'),
    ]

    operations = [
        migrations.AddField(
            model_name='contact',
            name='last_at',
            field=models.DateTimeField(db_index=True, default=None, null=True, verbose_name='最新消息时间'),
        ),
        migrations.AddField(
            model_name='contact',
            name='last_msg',
            field=models.JSONField(default=dict, verbose_name='最新消息内容'),
        ),
    ]
