import logging
from rest_framework import serializers
from django.utils.functional import cached_property

from server.applibs.billing.models import WXPay, BillDetail
from server.applibs.account.models import AuthUser, OAuthWechat
from server.corelib.hash_id import pk_hashid_decode


logger = logging.getLogger('kubrick.debug')


class ChargeWXPaySerializer(serializers.Serializer):
    """ 微信支付充值，统一下单 """

    amount = serializers.IntegerField(label='金额', required=True)

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    @staticmethod
    def validate_amount(value):
        amount_error_msg = '输入金额有误'
        if value in (100, 200, 500, 1000, 2000):
            return value
        raise serializers.ValidationError(amount_error_msg)

    def validate(self, attrs):
        openid_error_msg = '获取支付信息异常'
        try:
            oauth_wx = OAuthWechat.objects.get(usrid=self.current_user.pk)
        except OAuthWechat.DoesNotExist:
            raise serializers.ValidationError(openid_error_msg)
        attrs['openid'] = oauth_wx.mpa_openid
        return attrs

    def create(self, validated_data):
        amount = validated_data['amount']
        openid = validated_data['openid']
        inst = WXPay.objects.add_charge_unifiedorder(
            self.current_user.pk, openid, amount
        )
        return inst

    def update(self, instance, validated_data):
        pass


class CallBillWXPaySerializer(serializers.Serializer):
    """ 通话账单微信支付，统一下单 """

    hid = serializers.CharField(label='账单加密ID', required=True)

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    def validate_hid(self, value):
        bill_detail_error_msg = '无法获取账单'
        bill_detail_paid_msg = '该账单已支付'
        bill_detail_free_msg = '该账单已免单'
        try:
            usrid = self.current_user.pk
            bill_id = pk_hashid_decode(value)
            inst = BillDetail.objects.get(pk=bill_id, usrid=usrid)
        except Exception as exc:
            logger.exception(f'bill_detail__error {str(exc)}')
            raise serializers.ValidationError(bill_detail_error_msg)
        if inst.is_paid:
            raise serializers.ValidationError(bill_detail_paid_msg)
        elif inst.is_free:
            raise serializers.ValidationError(bill_detail_free_msg)
        return inst

    def validate(self, attrs):
        openid_error_msg = '获取支付信息异常'
        try:
            oauth_wx = OAuthWechat.objects.get(usrid=self.current_user.pk)
        except OAuthWechat.DoesNotExist:
            raise serializers.ValidationError(openid_error_msg)
        attrs['openid'] = oauth_wx.mpa_openid
        return attrs

    def create(self, validated_data):
        bill = validated_data['hid']
        openid = validated_data['openid']
        assert isinstance(bill, BillDetail), str(bill)
        inst = WXPay.objects.add_paycall_unifiedorder(
            self.current_user.pk, openid, bill.amount, bill.pk
        )
        return inst

    def update(self, instance, validated_data):
        pass


class WXPayQuerySerializer(serializers.Serializer):
    """ 微信支付充值，查询结果 """

    tradeno = serializers.CharField(label='订单号', required=True)

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    def validate_tradeno(self, value):
        wxpay = WXPay.objects.get(usrid=self.current_user.pk, trade_no=value)
        wxpay.query_order()
        return wxpay

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass
