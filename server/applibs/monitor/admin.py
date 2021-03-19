from django.contrib import admin

from server.djextend import admins
from server.applibs.monitor import models


@admin.register(models.APIReqCount)
class APIReqCountAdmin(admins.ReadonlyAdmin):
    list_filter = ('dt_req', 'method', 'status', 'route')
    list_display = (
        'pk', 'dt_req', 'route', 'method', 'status',
        'count', 'ct_user', 'rate', 'ms_avg', 'updated_at',
    )
    readonly_fields = (
        'dt_req', 'route', 'method', 'status', 'count', 'ct_user', 'rate',
        'ms_use', 'ms_avg', 'hosts', 'last', 'extra', 'created_at', 'updated_at',
    )

    def rate(self, obj):
        return obj.rate_auth

    rate.short_description = '登录请求量占比(%)'

    def ms_avg(self, obj):
        return obj.ms_avg

    ms_avg.short_description = '平均响应时间(ms)'

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(models.CountThirdApi)
class CountThirdApiAdmin(admins.ReadonlyAdmin):
    list_filter = ('dt_req', 'provider', 'action')
    list_display = (
        'pk', 'dt_req', 'provider', 'action', 'count',
        'ct_success', 'rate', 'ms_avg', 'updated_at',
    )
    readonly_fields = (
        'pk', 'dt_req', 'provider', 'action', 'count',
        'ct_success', 'rate', 'ms_avg', 'ct_exc', 'ct_error', 'ct_failure',
        'extra', 'created_at', 'updated_at', 'ms_success',
    )

    def rate(self, obj):
        return obj.rate

    rate.short_description = '成功比例(%)'

    def ms_avg(self, obj):
        return obj.ms_avg

    ms_avg.short_description = '平均响应时间(ms)'

    def has_add_permission(self, request, obj=None):
        return False
