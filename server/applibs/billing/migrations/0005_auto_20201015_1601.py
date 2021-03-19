# Generated by Django 3.1.2 on 2020-10-15 08:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0004_auto_20201013_1832'),
    ]

    operations = [
        migrations.AddField(
            model_name='wxpay',
            name='instid',
            field=models.BigIntegerField(db_index=True, default=0, verbose_name='关联记录'),
        ),
        migrations.AlterField(
            model_name='wxpay',
            name='pay_type',
            field=models.PositiveSmallIntegerField(choices=[(1, '充值'), (2, '打印'), (10, '通话账单')], default=0, verbose_name='类型'),
        ),
    ]