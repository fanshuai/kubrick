# Generated by Django 3.1.1 on 2020-09-15 07:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('outside', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='imageocr',
            name='ocr_type',
            field=models.PositiveSmallIntegerField(choices=[(2, '二维码'), (5, '车牌'), (11, '身份证正面'), (12, '身份证反面'), (33, '行驶证')], default=0, verbose_name='OCR类型'),
        ),
    ]
