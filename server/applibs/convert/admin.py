from django.contrib import admin

from server.djextend import admins
from server.applibs.convert import models


@admin.register(models.Contact)
class ContactAdmin(admins.ReadonlyAdmin):
    list_filter = ('unread', 'is_block', 'last_at')
    list_display = (
        'bid', 'convid', 'usrid', 'touchid', 'unread',
        'read_at', 'is_block', 'remark', 'last_at',
    )
    readonly_fields = (
        'bid', 'convid', 'usrid', 'touchid', 'last_at',
        'unread', 'read_at', 'is_block', 'keywords',
        'extra_json', 'created_at', 'updated_at',
    )
    search_fields = ('convid', 'usrid', 'touchid', 'remark', 'keywords')
    exclude = ('last_msg', 'extra',)

    def last_msg_json(self, obj):
        extra = getattr(obj, 'last_msg', {})
        return admins.json_format_html(extra)

    last_msg_json.short_description = '最新消息内容'


@admin.register(models.Conversation)
class ConversationAdmin(admins.ReadonlyAdmin):
    list_filter = ('count', 'last_at')
    list_display = (
        'convid', 'last_id', 'last_by', 'symbol',
        'members', 'count', 'called', 'last_at',
    )
    readonly_fields = (
        'bid', 'convid', 'last_id', 'last_by',
        'last_at', 'symbol', 'members', 'count', 'called',
        'attrs_json', 'extra_json', 'created_at', 'updated_at',
    )
    search_fields = ('convid', 'last_by', 'symbol', 'members')
    exclude = ('attrs', 'extra')

    def attrs_json(self, obj):
        return admins.json_format_html(obj.attrs)

    attrs_json.short_description = '自定义属性'


@admin.register(models.Message)
class MessageAdmin(admins.ReadonlyAdmin):
    list_filter = ('msg_type', 'reach', 'read_at', 'is_del', 'is_timed', 'created_at')
    list_display = (
        'bid', 'convid', 'sender', 'receiver', 'symbol', 'msg_type',
        'reach', 'read_at', 'is_del', 'is_timed', 'created_at',
    )
    readonly_fields = (
        'bid', 'convid', 'sender', 'receiver', 'symbol', 'timer', 'diff_at',
        'msg_type', 'msg_body_json', 'content', 'reach', 'read_at',
        'location_json', 'extra_json', 'created_at', 'updated_at',
    )
    search_fields = ('sender', 'receiver', 'symbol', 'content')
    exclude = ('msg_body', 'location', 'extra')

    def msg_body_json(self, obj):
        return admins.json_format_html(obj.msg_body)

    msg_body_json.short_description = '消息内容'

    def location_json(self, obj):
        return admins.json_format_html(obj.location)

    location_json.short_description = '位置信息'

    def has_change_permission(self, request, obj=None):
        return request.user.is_perm_admin


@admin.register(models.ReportUser)
class ReportUserAdmin(admins.ReadonlyAdmin):
    list_filter = ('is_disable', 'operator', 'count_user')
    list_display = (
        'touchid', 'is_disable', 'disabled_at', 'disable_txt',
        'count_report', 'count_user', 'operator', 'created_at',
    )
    readonly_fields = (
        'touchid', 'is_disable', 'disabled_at', 'disable_txt', 'active_txt',
        'count_report', 'count_user', 'operator', 'extra_json', 'created_at', 'updated_at',
    )
    exclude = ('extra',)
    search_fields = ('touchid', 'disable_txt', 'active_txt')

    def has_change_permission(self, request, obj=None):
        return request.user.is_perm_admin


@admin.register(models.ReportRecord)
class ReportRecordAdmin(admins.ReadonlyAdmin):
    list_filter = ('kind', 'is_offend', 'is_solved')
    list_display = (
        'id', 'usrid', 'touchid', 'kind', 'kind_txt',
        'is_offend', 'is_solved', 'operator', 'created_at',
    )
    readonly_fields = (
        'id', 'usrid', 'touchid', 'kind', 'kind_txt', 'is_offend', 'offended',
        'evidence', 'feedback', 'operator', 'extra_json', 'created_at', 'updated_at',
    )
    search_fields = ('usrid', 'touchid', 'kind_txt', 'offended')
    exclude = ('extra',)

    def has_change_permission(self, request, obj=None):
        return request.user.is_perm_admin
