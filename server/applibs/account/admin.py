from django.contrib import admin
from django.utils.safestring import mark_safe
from django.contrib.sessions.models import Session
from collections import OrderedDict

from server.djextend import admins
from server.applibs.account import models
from server.djextend.admins import json_format_html


@admin.register(models.AuthUser)
class AuthUserAdmin(admins.ReadonlyAdmin):
    exclude = ('user_permissions', 'groups', 'extra', 'password')
    list_filter = ('is_active', 'is_superuser', 'date_joined', 'last_login')
    list_display = (
        'bid', 'hid', 'name', 'username', 'is_active', 'is_superuser',
        'date_joined', 'last_login',
    )
    readonly_fields = (
        'bid', 'hid', 'name', 'username', 'is_pwd', 'date_joined', 'last_login', 'extra_json'
    )
    search_fields = ('bid', 'name', 'username')

    def hid(self, obj):
        return obj.hid

    hid.short_description = '外部ID'

    def is_pwd(self, obj):
        return obj.is_pwd

    is_pwd.short_description = '已设置密码'

    def has_change_permission(self, request, obj=None):
        return request.user.is_perm_admin


@admin.register(models.UserProfile)
class UserProfileAdmin(admins.ReadonlyAdmin):
    list_filter = ('gender', 'city', 'updated_at')
    list_display = ('usrid', 'gender', 'birthday', 'avatar', 'city', 'updated_at')
    readonly_fields = (
        'usrid', 'gender', 'birthday', 'avatar', 'bio',
        'extra_json', 'created_at', 'updated_at',
    )
    search_fields = ('usrid',)
    exclude = ('extra',)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_filter = ('expire_date',)
    list_display = ('session_key', 'expire_date', 'usrid')
    fields = ('session_key', 'expire_date', 'data_json', 'usrid')

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        return self.fields

    def get_actions(self, request):
        return OrderedDict()

    @staticmethod
    def session_data(obj):
        return obj.get_decoded()

    def data_json(self, obj):
        return admins.json_format_html(self.session_data(obj))

    data_json.short_description = '内容'

    def usrid(self, obj):
        return self.session_data(obj).get('_auth_user_id')

    usrid.short_description = '用户'


@admin.register(models.UserDevice)
class UserDeviceAdmin(admins.ReadonlyAdmin):
    list_filter = ('app_type', 'is_valid', 'is_online', 'version', 'created_at', 'activated_at')
    list_display = (
        'bid', 'usrid', 'device_key', 'app_type', 'device_name',
        'req_count', 'activated_at', 'is_valid', 'created_at',
    )
    readonly_fields = (
        'bid', 'key', 'usrid', 'user_agent', 'ua_info_json', 'device_name', 'device_key', 'app_type', 'version',
        'client_ip', 'is_routable',  'referer', 'last_uri', 'activated_at', 'logout_at', 'req_count',
        'extra_json', 'is_valid', 'is_online', 'logout_at', 'created_at', 'updated_at',
    )
    search_fields = ('bid', 'usrid', 'user_agent', 'device_name', 'client_ip', 'is_routable', 'version')
    exclude = ('ua_info', 'extra',)

    def ua_info_json(self, obj):
        ua_info = getattr(obj, 'ua_info', {})
        return json_format_html(ua_info)

    ua_info_json.short_description = 'UA信息'


@admin.register(models.Phone)
class PhoneAdmin(admins.ReadonlyAdmin):
    list_filter = ('carrier', 'nation', 'region', 'is_verified')
    list_display = ('bid', 'number', 'usrid', 'carrier', 'nation', 'region', 'is_verified', 'order', 'created_at')
    readonly_fields = (
        'bid', 'number', 'fmt_intl', 'show', 'usrid', 'national', 'shahash',
        'carrier', 'nation', 'region', 'is_verified', 'verified_at',
        'order', 'extra_json', 'created_at', 'updated_at',
    )
    search_fields = ('number', 'usrid')
    exclude = ('extra',)

    def show(self, obj):
        return obj.show

    show.short_description = '脱敏显示'

    def fmt_intl(self, obj):
        return obj.fmt_intl

    fmt_intl.short_description = '格式化'


@admin.register(models.UserCode)
class UserCodeAdmin(admins.ReadonlyAdmin):
    list_filter = ('views', 'pages', 'updated_at')
    list_display = (
        'usrid', 'code', 'fmt', 'views', 'pages',
        'qrimg', 'version', 'created_at', 'updated_at',
    )
    readonly_fields = (
        'usrid', 'code',  'version', 'fmt',
        'views', 'pages', 'qrimg', 'qrimg_url',
        'hotp_at', 'extra_json', 'created_at', 'updated_at',
    )
    search_fields = ('usrid', 'code')
    exclude = ('extra',)

    def qrimg_url(self, obj):
        url = obj.qr_uri
        url_tag = f'<a href="{url}" target="_blank">{url}</a>'
        return mark_safe(url_tag)

    qrimg_url.short_description = '用户码内容'
    qrimg_url.allow_tags = True


@admin.register(models.OAuthWechat)
class OAuthWechatAdmin(admins.ReadonlyAdmin):
    list_filter = ('gender', 'country', 'province', 'city', 'created_at')
    list_display = (
        'bid', 'usrid', 'unionid', 'nick_name', 'gender',
        'country', 'province', 'city', 'created_at',
    )
    readonly_fields = (
        'bid', 'usrid', 'unionid', 'nick_name', 'gender',
        'country', 'province', 'city', 'link_at', 'avatar',
        'openids_json', 'context_json', 'extra_json', 'created_at', 'updated_at',
    )
    search_fields = ('bid', 'usrid', 'unionid', 'nick_name')
    exclude = ('extra', 'context', 'openids')

    def context_json(self, obj):
        context = getattr(obj, 'context', {})
        return admins.json_format_html(context)

    context_json.short_description = 'OAuth用户信息'

    def openids_json(self, obj):
        context = getattr(obj, 'openids', {})
        return admins.json_format_html(context)

    openids_json.short_description = '不同应用标识'


@admin.register(models.OAuthWechatApp)
class OAuthWechatAppAdmin(admins.ReadonlyAdmin):
    list_filter = ('app_type', 'session_at', 'created_at')
    list_display = (
        'bid', 'hid', 'openid', 'app_type', 'usrid',
        'unionid', 'session_at', 'created_at',
    )
    readonly_fields = (
        'bid', 'hid', 'openid', 'app_type', 'usrid', 'unionid',
        'session_key', 'session_at', 'created_at', 'updated_at', 'extra_json',
    )
    search_fields = ('usrid', 'unionid', 'openid')
    exclude = ('extra',)


# @admin.register(models.IDCard)
class IDCardAdmin(admins.ReadonlyAdmin):
    list_filter = ('sex', 'birth', 'nationality', 'is_valid')
    list_display = ('bid', 'usrid', 'name', 'sex', 'nationality', 'birth', 'end_date', 'is_valid')
    readonly_fields = (
        'bid', 'usrid', 'name', 'sex', 'nationality', 'birth', 'authority', 'start_date', 'end_date',
        'img_front', 'img_back', 'is_valid', 'extra_json', 'created_at', 'updated_at',
    )
    search_fields = ('bid', 'usrid', 'name')
    exclude = ('extra',)
