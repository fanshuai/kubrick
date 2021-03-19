import logging
from rest_framework import serializers
from django.utils.functional import cached_property
from sentry_sdk import capture_message

from server.applibs.release.models import Symbol
from server.applibs.account.models import AuthUser, Phone
from server.corelib.dealer.deal_string import filter_newlines
from server.third.aliyun.anti import txt_spam_cached
from server.third.aliyun.oss import oss_has_key


logger = logging.getLogger('kubrick.debug')


class VehicleLicenseImgSerializer(serializers.Serializer):
    """ 行驶证识别，车辆绑定 """

    img = serializers.CharField(label='行驶证照片', required=True)

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    def validate_img(self, value):
        no_img_error_msg = '无法获取行驶证照片'
        max_count_error_msg = '最多只能绑定5辆车'
        count = Symbol.objects.user_symbol_qs(self.current_user.pk).count()
        if count >= 5:
            raise serializers.ValidationError(max_count_error_msg)
        if not oss_has_key(value):
            raise serializers.ValidationError(no_img_error_msg)
        return value

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class SymbolTitleSerializer(serializers.Serializer):
    """ 场景码 别名 """
    title = serializers.CharField(label='别名', max_length=8, required=True, allow_blank=True)

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    @cached_property
    def current_symbol(self):
        symbol = self.context['symbol']
        assert isinstance(symbol, Symbol)
        return symbol

    def validate_title(self, value):
        """ 别名 AntiSpam """
        if not value:
            return ''
        usrid = self.current_user.pk
        symbolid = self.current_symbol.pk
        symbol_qs = Symbol.objects.user_symbol_qs(usrid)
        if symbol_qs.filter(title=value).exclude(pk=symbolid).exists():
            title_used_msg = f'已使用过该名'
            raise serializers.ValidationError(title_used_msg)
        spam_desc = txt_spam_cached(value)
        if not spam_desc:
            return value
        capture_message('symbol_title_spam__hit')
        logger.warning(f'symbol_title_spam__hit {value}: [{usrid}] {spam_desc}')
        illegal_error_msg = f'可能含[{spam_desc}]内容'
        raise serializers.ValidationError(illegal_error_msg)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class SymbolSelfdomSerializer(serializers.Serializer):
    """ 场景码 自定义签名 """
    selfdom = serializers.CharField(label='自定义签名', default='', max_length=50, allow_blank=True)

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    def validate_selfdom(self, value):
        """ 自定义签名 AntiSpam """
        value = filter_newlines(value)
        spam_desc = txt_spam_cached(value)
        if not spam_desc:
            return value
        usrid = self.current_user.pk
        capture_message('symbol_selfdom_spam__hit')
        logger.warning(f'symbol_selfdom_spam__hit {value}: [{usrid}] {spam_desc}')
        illegal_error_msg = f'可能含[{spam_desc}]内容'
        raise serializers.ValidationError(illegal_error_msg)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class SymbolUnbindSerializer(serializers.Serializer):
    """ 场景码解除绑定，验证验证码 """
    captcha = serializers.CharField(required=True, max_length=10)

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    def validate(self, attrs):
        no_phone_msg = '暂未绑定手机号'
        captcha_error_msg = '验证码不正确'
        captcha = attrs['captcha']
        phone = Phone.objects.user_phone_main(self.current_user.pk)
        if not phone:
            raise serializers.ValidationError(no_phone_msg)
        is_ok = phone.captcha_verify_for_symbol_strike(captcha)
        if not is_ok:
            raise serializers.ValidationError(captcha_error_msg)
        return attrs

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass
