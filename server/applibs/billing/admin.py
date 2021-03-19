from django.contrib import admin

from server.djextend import admins
from server.applibs.billing import models


@admin.register(models.WXPay)
class WXPayAdmin(admins.ReadonlyAdmin):
    list_filter = ('status', 'pay_type', 'trade_at', 'updated_at')
    list_display = (
        'bid', 'usrid', 'amount', 'body', 'openid', 'trade_no',
        'pay_type', 'status', 'instid', 'trade_at', 'updated_at',
    )
    readonly_fields = (
        'bid', 'usrid', 'amount', 'body', 'openid', 'trade_no', 'pay_type', 'status', 'instid',
        'trade_at', 'transaction', 'prepay_id', 'extra_json', 'created_at', 'updated_at',
    )
    search_fields = ('openid', 'trade_no', 'instid')
    exclude = ('extra',)


@admin.register(models.BillMonth)
class BillMonthAdmin(admins.ReadonlyAdmin):
    list_filter = ('month', 'updated_at')
    list_display = ('pk', 'month', 'usrid', 'count', 'amount', 'free', 'updated_at')
    readonly_fields = (
        'pk', 'month', 'usrid', 'count', 'amount', 'free',
        'extra_json', 'created_at', 'updated_at',
    )
    search_fields = ('usrid', 'month')
    exclude = ('extra',)


@admin.register(models.BillDetail)
class BillDetailAdmin(admins.ReadonlyAdmin):
    list_filter = ('bill_at', 'is_free', 'is_paid', 'is_del')
    list_display = (
        'pk', 'usrid', 'amount', 'summary', 'bill_at', 'call_id',
        'is_free', 'is_paid', 'pay_id', 'month_id', 'is_del'
    )
    readonly_fields = (
        'pk', 'usrid', 'amount', 'summary', 'bill_at', 'call_id', 'is_free', 'is_paid',
        'pay_id', 'month_id', 'is_del', 'extra_json', 'created_at', 'updated_at',
    )
    search_fields = ('usrid', 'call_id', 'pay_id', 'month_id')
    exclude = ('extra',)
