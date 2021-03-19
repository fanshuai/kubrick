from django.urls import reverse
from django.contrib import admin
from django.utils.safestring import mark_safe

from server.djextend import admins
from server.applibs.release import models
from server.djextend.admins import json_format_html
from server.corelib.dealer import deal_time
from server.constant import mochoice as mc


@admin.register(models.Symbol)
class SymbolAdmin(admins.ReadonlyAdmin):
    list_filter = ('scene', 'status', 'created_at')
    list_display = (
        'bid', 'usrid', 'symbol', 'qrimg_show', 'status',
        'views', 'pages', 'scene', 'title', 'created_at',
    )
    readonly_fields = (
        'bid', 'usrid', 'symbol', 'fmt', 'hotp_at', 'scene', 'views', 'pages',
        'qrimg_url', 'qrimg_show', 'selfdom', 'title', 'ct_trigger',
        'bound_at', 'version', 'extra_json', 'created_at', 'updated_at',
    )
    search_fields = ('symbol',)
    exclude = ('extra',)

    def qrimg_url(self, obj):
        if not obj.symbol:
            return ''
        url = obj.qr_uri
        url_tag = f'<a href="{url}" target="_blank">{url}</a>'
        return mark_safe(url_tag)

    qrimg_url.short_description = '场景码内容'
    qrimg_url.allow_tags = True

    def qrimg_show(self, obj):
        if not obj.symbol:
            return ''
        url = reverse('djadmin_qrimg', kwargs=dict(code=obj.symbol))
        url_tag = f'<a href="{url}" target="_blank">{url}</a>'
        return mark_safe(url_tag)

    qrimg_show.short_description = '场景码图片'
    qrimg_show.allow_tags = True


@admin.register(models.Subject)
class SubjectAdmin(admins.ReadonlyAdmin):
    list_filter = ('scene', 'designer', 'batch', 'created_at')
    list_display = (
        'pk', 'name', 'scene', 'spuid', 'designer', 'batch',
        'activated', 'total', 'rate_activated', 'created_at',
    )
    readonly_fields = (
        'pk', 'batch', 'activated', 'total', 'rate_activated',
        'record_json', 'extra_json', 'created_at', 'updated_at',
    )
    search_fields = ('name', 'designer', 'summary', 'spuid')
    exclude = ('record', 'extra')

    def has_add_permission(self, request, obj=None):
        return request.user.is_perm_admin

    def has_change_permission(self, request, obj=None):
        return request.user.is_perm_admin

    def record_json(self, obj):
        record = getattr(obj, 'record', {})
        return json_format_html(record)

    record_json.short_description = '发行记录'


@admin.register(models.Publication)
class PublicationAdmin(SymbolAdmin):
    list_filter = (
        'subject__name', 'subject__designer',
        'scene', 'status', 'batch', 'channel',
        'published_at', 'activated_at', 'created_at',
    )
    list_display = (
        'pk', 'subject', 'usrid', 'symbol', 'scene',
        'status', 'qrimg_show', 'batch', 'channel',
        'published_at', 'activated_at', 'created_at',
    )
    readonly_fields = (
        'pk', 'subject', 'usrid', 'symbol', 'fmt', 'scene', 'status', 'batch',
        'hotp_at', 'qrimg', 'qrimg_url', 'qrimg_show', 'version', 'channel',
        'published_at', 'activated_at', 'extra_json', 'created_at', 'updated_at',
    )
    search_fields = ('symbol', 'usrid', 'channel')
    actions = ('init_to_prepared', 'prepared_to_init')
    exclude = ('extra',)

    def init_to_prepared(self, request, queryset):
        now = deal_time.get_now()
        rows_updated = queryset.filter(
            status=mc.PublishStatus.Init,
        ).update(
            published_at=now,
            status=mc.PublishStatus.Prepared,
        )
        self.message_user(request, f'[{rows_updated}]条[初始化]记录已标记为[已就绪]。')
    init_to_prepared.short_description = '[初始化]标记为[已就绪]'

    def prepared_to_init(self, request, queryset):
        rows_updated = queryset.filter(
            status=mc.PublishStatus.Prepared,
        ).update(
            published_at=None,
            status=mc.PublishStatus.Init,
        )
        self.message_user(request, f'[{rows_updated}]条[已就绪]记录已标记为[初始化]。')
    prepared_to_init.short_description = '[已就绪]回滚为[初始化]'

    def has_change_permission(self, request, obj=None):
        return request.user.is_perm_admin


@admin.register(models.Vehicle)
class VehicleAdmin(admins.ReadonlyAdmin):
    list_filter = ('vehicle_type', 'relation')
    list_display = (
        'pk', 'symbol', 'usrid', 'vehicle_type',
        'vehicle_num', 'relation', 'created_at',
    )
    readonly_fields = (
        'pk', 'symbol', 'usrid', 'vehicle_num', 'vehicle_type',
        'relation', 'shahash', 'license_id', 'extra_json',
        'created_at', 'updated_at',
    )
    search_fields = ('symbol', 'vehicle_num')
    exclude = ('extra',)


@admin.register(models.VehicleLicense)
class VehicleLicenseAdmin(admins.ReadonlyAdmin):
    list_filter = ('vehicle_type', 'use_character', 'is_verified')
    list_display = (
        'pk', 'usrid', 'plate_num', 'vehicle_type', 'use_character',
        'owner', 'model', 'verified_at', 'created_at',
    )
    readonly_fields = (
        'pk', 'usrid', 'plate_num', 'vehicle_type', 'use_character',
        'oss_url', 'owner', 'model', 'vin', 'engine_num', 'address',
        'register_date', 'issue_date', 'verified_at', 'verified_at',
        'reason', 'extra_json', 'created_at', 'updated_at',
    )
    search_fields = ('vehicle_num', 'engine_num')
    exclude = ('extra',)

    def oss_url(self, obj):
        return obj.url_watermark

    oss_url.short_description = '图片地址'
