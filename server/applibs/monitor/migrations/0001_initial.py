# Generated by Django 3.1 on 2020-08-27 06:29

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CountThirdApi',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, verbose_name='更新时间')),
                ('extra', models.JSONField(default=dict, verbose_name='扩展数据')),
                ('dt_req', models.DateField(auto_now_add=True, verbose_name='日期')),
                ('provider', models.CharField(choices=[('aliyun', '阿里云'), ('wechat', '微信'), ('ytx', '云迅(讯众)')], default='', max_length=100, verbose_name='服务商')),
                ('action', models.URLField(choices=[('SendSms', '阿里云-短信服务-发送短信'), ('QuerySendDetails', '阿里云-短信服务-查询结果'), ('SingleSendMail', '阿里云-邮件推送-单一发信接口'), ('ImageSyncScan', '阿里云-内容安全-图片OCR识别'), ('TextScan', '阿里云-内容安全-文本反垃圾'), ('auth.getAccessToken', '微信-小程序-接口调用凭据'), ('auth.code2Session', '微信-小程序-登录凭证校验'), ('auth.getPaidUnionId', '微信-小程序-获取支付UnionId'), ('security.msgSecCheck', '微信-小程序-内容安全文本违规'), ('subscribeMessage.send', '微信-小程序-发送订阅消息'), ('xunzhong.dailBackCall', '云讯-双向呼叫'), ('xunzhong.queryBlance', '云讯-查询余额'), ('xunzhong.callCdr', '云讯-话单获取')], default='', max_length=100, verbose_name='方法')),
                ('count', models.PositiveIntegerField(default=0, verbose_name='请求量')),
                ('ct_exc', models.PositiveIntegerField(default=0, verbose_name='请求异常量')),
                ('ct_error', models.PositiveIntegerField(default=0, verbose_name='返回异常量')),
                ('ct_failure', models.PositiveIntegerField(default=0, verbose_name='返回失败量')),
                ('ct_success', models.PositiveIntegerField(default=0, verbose_name='成功量')),
                ('ms_success', models.BigIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'CountThirdApi',
                'verbose_name_plural': 'CountThirdApi',
                'db_table': 'k_mt_count_thirdapi',
                'ordering': ('-pk',),
                'unique_together': {('dt_req', 'provider', 'action')},
            },
        ),
        migrations.CreateModel(
            name='APIReqCount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, verbose_name='更新时间')),
                ('extra', models.JSONField(default=dict, verbose_name='扩展数据')),
                ('dt_req', models.DateField(auto_now_add=True, verbose_name='日期')),
                ('route', models.URLField(default='', verbose_name='路由')),
                ('method', models.SlugField(default='', max_length=10, verbose_name='方法')),
                ('status', models.PositiveSmallIntegerField(default=0, verbose_name='响应码')),
                ('count', models.PositiveIntegerField(default=0, verbose_name='请求量')),
                ('ct_user', models.PositiveIntegerField(default=0, verbose_name='已登录请求量')),
                ('ms_use', models.BigIntegerField(default=0, verbose_name='请求毫秒数')),
                ('hosts', models.JSONField(default=dict, verbose_name='主机')),
                ('last', models.JSONField(default=dict, verbose_name='最后')),
            ],
            options={
                'verbose_name': 'APIReqCount',
                'verbose_name_plural': 'APIReqCount',
                'db_table': 'k_mt_apireq_count',
                'ordering': ('-pk',),
                'unique_together': {('dt_req', 'route', 'method', 'status')},
            },
        ),
    ]
