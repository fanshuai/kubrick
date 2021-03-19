from django.contrib import admin

from server.djextend import admins
from server.applibs.outside import models


@admin.register(models.ImageOcr)
class ImageOcrAdmin(admins.ReadonlyAdmin):
    list_filter = ('ocr_type', 'suggestion', 'is_victor')
    list_display = (
        'bid', 'usrid', 'ocr_type', 'rate', 'suggestion',
        'is_victor', 'ocr_use_ms', 'created_at',
    )
    readonly_fields = (
        'bid', 'usrid', 'ocr_type', 'rate',  'suggestion',
        'oss_url', 'is_victor', 'reason', 'ocr_use_ms',
        'result_json', 'extra_json', 'created_at', 'updated_at',
    )
    exclude = ('result', 'extra')

    def result_json(self, obj):
        return admins.json_format_html(obj.result_dic)

    result_json.short_description = '结果'

    def oss_url(self, obj):
        return obj.oss_url

    oss_url.short_description = '图片地址'


@admin.register(models.ImageScan)
class ImageScanAdmin(admins.ReadonlyAdmin):
    list_filter = ('mode', 'is_valid')
    list_display = (
        'bid', 'usrid', 'mode', 'use_ms',
        'is_valid',  'reason', 'created_at',
    )
    readonly_fields = (
        'bid', 'usrid', 'oss_key', 'mode', 'reason', 'use_ms', 'oss_url',
        'is_valid', 'result_json', 'location_json', 'extra_json', 'created_at', 'updated_at',
    )
    exclude = ('location', 'result', 'extra')

    def location_json(self, obj):
        return admins.json_format_html(obj.location)

    location_json.short_description = '位置信息'

    def result_json(self, obj):
        return admins.json_format_html(obj.result)

    result_json.short_description = '结果'

    def oss_url(self, obj):
        return obj.oss_url

    oss_url.short_description = '图片地址'


@admin.register(models.SmsRecord)
class SmsRecordAdmin(admins.ReadonlyAdmin):
    list_filter = ('scene', 'status', 'send_at')
    list_display = (
        'bid', 'scene', 'number', 'usrid', 'touchid', 'template',
        'status',  'report_at', 'send_at', 'instid', 'err_msg',
    )
    readonly_fields = (
        'bid', 'scene', 'number', 'usrid', 'touchid', 'template',
        'status', 'report_at', 'send_at', 'instid', 'params_json',
        'err_msg', 'extra_json', 'created_at', 'updated_at',
    )
    exclude = ('params', 'extra')

    def params_json(self, obj):
        params = getattr(obj, 'params', {})
        return admins.json_format_html(params)

    params_json.short_description = '模板参数'


@admin.register(models.CallRecord)
class CallRecordAdmin(admins.ReadonlyAdmin):
    list_filter = ('status', 'call_state', 'created_at')
    list_display = (
        'bid', 'msgid', 'usrid', 'touchid', 'req_id', 'status',
        'duration', 'call_ts', 'call_state', 'cost', 'fee', 'created_at',
    )
    readonly_fields = (
        'bid', 'callid', 'msgid', 'usrid', 'touchid', 'req_id', 'status',
        'caller', 'called', 'duration', 'call_ts', 'call_state', 'cost', 'fee',
        'provider', 'callers_at', 'callere_at', 'calleds_at', 'callede_at',
        'status_at', 'extra_json', 'created_at', 'updated_at',
    )
    search_fields = ('msgid', 'req_id')
    exclude = ('is_record', 'record_file', 'extra')


@admin.register(models.Configuration)
class ConfigurationAdmin(admins.ReadonlyAdmin):
    list_filter = ('cate', 'key', 'sort', 'is_active', 'begin_at', 'finish_at')
    list_display = ('id', 'cate', 'key', 'value', 'sort', 'is_active', 'begin_at', 'finish_at')
    readonly_fields = ('id', 'extra_json', 'created_at', 'updated_at')
    search_fields = ('key', 'value')
    exclude = ('extra',)

    def has_add_permission(self, request, obj=None):
        return request.user.is_perm_admin

    def has_change_permission(self, request, obj=None):
        return request.user.is_perm_admin
