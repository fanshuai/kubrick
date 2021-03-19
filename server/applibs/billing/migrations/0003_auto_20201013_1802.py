# Generated by Django 3.1.2 on 2020-10-13 10:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_auto_20201012_1459'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='billdetail',
            name='instid',
        ),
        migrations.AddField(
            model_name='billdetail',
            name='call_id',
            field=models.BigIntegerField(default=None, null=True, unique=True, verbose_name='通话记录'),
        ),
        migrations.AddField(
            model_name='billdetail',
            name='is_paid',
            field=models.BooleanField(default=False, verbose_name='是否已支付'),
        ),
        migrations.AddField(
            model_name='billdetail',
            name='pay_id',
            field=models.BigIntegerField(db_index=True, default=0, verbose_name='支付记录'),
        ),
        migrations.AlterField(
            model_name='billdetail',
            name='bill_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='入账时间'),
        ),
    ]