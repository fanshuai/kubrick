# Generated by Django 3.1.1 on 2020-09-13 11:42

from django.db import migrations, models
import server.third.aliyun.oss.oss_path


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0002_auto_20200907_1953'),
    ]

    operations = [
        migrations.AddField(
            model_name='usercode',
            name='qrimg',
            field=models.ImageField(default=None, null=True, upload_to=server.third.aliyun.oss.oss_path.usercode_qrimg, verbose_name='二维码'),
        ),
    ]
