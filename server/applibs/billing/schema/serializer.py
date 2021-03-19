from rest_framework import serializers

from .. import models


class BillDetailSerializer(serializers.ModelSerializer):
    """ 账单明细 """
    class Meta:
        model = models.BillDetail
        fields = ('hid', 'amount', 'at', 'paid', 'free', 'desc')

    at = serializers.ReadOnlyField(label='入账时间', source='humanize_at')
    free = serializers.ReadOnlyField(label='是否已免单', source='is_free')
    paid = serializers.ReadOnlyField(label='是否已支付', source='is_paid')
    desc = serializers.ReadOnlyField(label='摘要', source='summary')


class BillMonthSerializer(serializers.ModelSerializer):
    """ 月度账单明细 """
    class Meta:
        model = models.BillMonth
        fields = ('count', 'amount', 'fmt', 'details')

    fmt = serializers.ReadOnlyField(label='月份', source='month_fmt')
    details = BillDetailSerializer(label='明细', source='detail_qs', many=True)
