# Generated by Django 3.1.2 on 2020-10-13 10:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0003_auto_20201013_1802'),
    ]

    operations = [
        migrations.AlterField(
            model_name='billdetail',
            name='bill_at',
            field=models.DateTimeField(db_index=True, default=None, null=True, verbose_name='入账时间'),
        ),
    ]
