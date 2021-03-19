# Generated by Django 3.1.1 on 2020-09-10 10:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('release', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='symbol',
            name='status',
            field=models.PositiveSmallIntegerField(choices=[(0, '初始化'), (20, '已绑定'), (24, '已关闭'), (40, '已删除'), (44, '已作废')], default=0, verbose_name='状态'),
        ),
        migrations.AlterIndexTogether(
            name='symbol',
            index_together={('scene', 'status', 'version')},
        ),
        migrations.RemoveField(
            model_name='symbol',
            name='ct_call',
        ),
        migrations.RemoveField(
            model_name='symbol',
            name='is_pre',
        ),
        migrations.RemoveField(
            model_name='symbol',
            name='limit_at',
        ),
        migrations.RemoveField(
            model_name='symbol',
            name='ocropen',
        ),
    ]