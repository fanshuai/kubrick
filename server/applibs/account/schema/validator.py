import logging
from django.contrib import auth
from django.contrib.auth import password_validation
from django.utils.functional import cached_property
from sentry_sdk import capture_exception, capture_message
from rest_framework import serializers

from server.constant import mochoice as mc
from server.third.aliyun.anti import txt_spam_cached
from server.third.aliyun.oss import oss_has_key, oss_sign_url
from server.corelib.dealer.deal_string import filter_newlines
from server.corelib.dealer.deal_phone import format_phonenumber
from server.applibs.account.models import (
    AuthUser, Phone, UserDevice, IDCard,
    OAuthWechat, OAuthWechatApp,
)
from server.third.wechat.crypte import wx_data_decrypt
from server.corelib.hash_id import pk_hashid_decode

logger = logging.getLogger('kubrick.debug')


class LoginSerializer(serializers.Serializer):
    """ 密码登录 """
    number = serializers.CharField(label='手机号', max_length=20, required=True)
    password = serializers.CharField(label='密码', max_length=50, required=True)

    @staticmethod
    def validate_number(value):
        phone_error_msg = '请确认手机号输入'
        number, message = format_phonenumber(value)
        if not number:
            raise serializers.ValidationError(phone_error_msg)
        try:
            inst = Phone.objects.get(number=value, is_verified=True)
            usrid = inst.usrid
            assert usrid > 0
        except (AssertionError, Phone.DoesNotExist):
            raise serializers.ValidationError(phone_error_msg)
        return usrid

    def validate(self, attrs):
        user_disabled_msg = '账号暂不可用'
        invalid_login_msg = '无效的手机号或密码'
        usrid, password = attrs['number'], attrs['password']
        user = auth.authenticate(pk=usrid, password=password)
        if not user:
            raise serializers.ValidationError(invalid_login_msg)
        if not user.is_active:
            raise serializers.ValidationError(user_disabled_msg)
        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class SigninSerializer(serializers.Serializer):
    """ 手机号登录，短信验证验证码 """
    number = serializers.CharField(label='手机号', max_length=20, required=True)
    captcha = serializers.CharField(required=True, max_length=10)

    @cached_property
    def current_unionid(self):
        unionid = self.context['unionid']
        return unionid

    @staticmethod
    def validate_number(value):
        phone_error_msg = '请确认手机号输入'
        invalid_number_msg = '手机号无效或暂不支持'
        number, message = format_phonenumber(value)
        if not number:
            raise serializers.ValidationError(invalid_number_msg)
        try:
            Phone.objects.get(number=number)
        except Phone.DoesNotExist:
            raise serializers.ValidationError(phone_error_msg)
        return number

    def validate(self, attrs):
        user_disabled_msg = '账号暂不可用'
        captcha_error_msg = '请确认验证码输入'
        no_oauth_info_msg = '获取微信认证信息失败'
        try:
            oauth_inst = OAuthWechat.objects.get(unionid=self.current_unionid)
        except (KeyError, OAuthWechat.DoesNotExist):
            raise serializers.ValidationError(no_oauth_info_msg)
        number, captcha = attrs['number'], attrs['captcha']
        phone = Phone.objects.get(number=number)
        user = phone.captcha_verify_for_sign(captcha)
        if not isinstance(user, AuthUser):
            raise serializers.ValidationError(captcha_error_msg)
        if not user.is_active:
            raise serializers.ValidationError(user_disabled_msg)
        attrs['oauth_inst'] = oauth_inst
        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class PasswordSerializer(serializers.Serializer):
    """ 设定或修改密码 """
    captcha = serializers.CharField(required=True, min_length=4, max_length=8)
    password = serializers.CharField(required=True, max_length=50)

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    def validate_captcha(self, value):
        no_phone_msg = '暂未绑定手机号'
        captcha_error_msg = '验证码输入有误'
        phone = Phone.objects.user_phone_main(self.current_user.pk)
        if not phone:
            raise serializers.ValidationError(no_phone_msg)
        is_ok = phone.captcha_verify_for_pwd(value, scene=mc.PNVScene.Password)
        if not is_ok:
            raise serializers.ValidationError(captcha_error_msg)
        return value

    def validate_password(self, value):
        try:
            password_validation.validate_password(value, user=self.current_user)
        except password_validation.ValidationError as exc:
            pwd_error_msg = '，'.join(exc.messages)
            raise serializers.ValidationError(pwd_error_msg)
        return value

    def validate(self, attrs):
        password = attrs['password']
        self.current_user.new_password(password)
        return attrs

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class WXCodeSessionSerializer(serializers.Serializer):
    """ 微信小程序CodeSession """
    code = serializers.CharField(required=True)

    def validate(self, attrs):
        user_disabled_msg = '账号暂不可用'
        try:
            code = attrs['code']
            oauth_wxapp = OAuthWechatApp.objects.oauth_wechat_mpapp_up(code)
            user = oauth_wxapp.user_info
        except Exception as exc:
            logger.warning(f'oauth_wechat_mpapp_up__error')
            raise serializers.ValidationError(f'{str(exc)}')
        if oauth_wxapp.usrid and (not user.is_active):
            raise serializers.ValidationError(user_disabled_msg)
        attrs['oauth_wxapp'] = oauth_wxapp
        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class WXUserInfoSerializer(serializers.Serializer):
    """ 微信小程序UserInfo """
    code = serializers.CharField(required=True)
    encrypted = serializers.CharField(required=True)
    iv = serializers.CharField(required=True)

    def validate(self, attrs):
        encrypted, code, iv = attrs['encrypted'], attrs['code'], attrs['iv']
        try:
            oauth_wx = OAuthWechat.objects.oauth_wechat_mpa_goc(code, encrypted, iv)
        except Exception as exc:
            logger.warning(f'oauth_wechat_mpa_goc__error')
            raise serializers.ValidationError(f'{str(exc)}')
        attrs['oauth_wx'] = oauth_wx
        return attrs

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class ProfileSerializer(serializers.Serializer):
    """ 个人信息修改 """
    name = serializers.CharField(label='名字', max_length=15, required=False)
    gender = serializers.CharField(label='性别', required=False)
    avatar = serializers.CharField(label='头像', required=False)
    # area = serializers.ListField(label='地区', required=False)

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    def validate_name(self, value):
        usrid = self.current_user.pk
        too_long_msg = '长度超过限制'
        value = value.replace(' ', '')
        value = value.replace('*', '')
        if not (0 < len(value) < 16):
            raise serializers.ValidationError(too_long_msg)
        spam_desc = txt_spam_cached(value)
        if spam_desc:
            capture_message(f'profile_name_spam__hit {spam_desc}')
            logger.warning(f'profile_name_spam__hit {value}: [{usrid}] {spam_desc}')
            illegal_error_msg = f'可能含[{spam_desc}]内容'
            raise serializers.ValidationError(illegal_error_msg)
        self.current_user.set_name(value)
        return value

    def validate_gender(self, value):
        if str(value).isdigit() and (int(value) in mc.UserGender):
            self.current_user.profile.set_gender(int(value))
        return value

    def validate_avatar(self, value):
        if oss_has_key(value):
            url = oss_sign_url(value)
            self.current_user.profile.set_avatar(url, compress=True)
        return value

    def validate_area(self, value):
        input_error_msg = '地区格式有误'
        set_region_error_msg = '地区暂不可用'
        if not (isinstance(value, list) and len(value) == 2):
            raise serializers.ValidationError(input_error_msg)
        try:
            self.current_user.profile.set_region(value)
        except Exception as exc:
            capture_exception(exc)
            logger.exception(f'validate_area__error {str(exc)}')
            raise serializers.ValidationError(set_region_error_msg)
        return value

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class ProfileBioSerializer(serializers.Serializer):
    """ 用户 个性签名 """
    bio = serializers.CharField(label='个性签名', max_length=50, required=True, allow_blank=True)

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    def validate_bio(self, value):
        """ 个性签名 AntiSpam """
        usrid = self.current_user.pk
        value = filter_newlines(value)
        spam_desc = txt_spam_cached(value)
        if spam_desc:
            capture_message(f'profile_bio_spam__hit {spam_desc}')
            logger.warning(f'profile_bio_spam__hit {value}: [{usrid}] {spam_desc}')
            illegal_error_msg = f'可能含[{spam_desc}]内容'
            raise serializers.ValidationError(illegal_error_msg)
        self.current_user.profile.set_bio(value)
        return value

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class PhoneAddSerializer(serializers.Serializer):
    """ 手机号绑定，发送验证码 """
    number = serializers.CharField(label='手机号', max_length=20, required=True)

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    def validate_number(self, value):
        invalid_number_msg = '手机号无效或暂不支持'
        has_bind_by_self_msg = '你已绑定过该手机号'
        has_bind_by_other_msg = '该手机号已被绑定'
        max_count_error_msg = f'最多只能绑定{Phone.limit}个手机号'
        phone_qs = Phone.objects.user_phone_qs(self.current_user.pk)
        if phone_qs.count() >= Phone.limit:
            raise serializers.ValidationError(max_count_error_msg)
        number, message = format_phonenumber(value)
        if not number:
            raise serializers.ValidationError(invalid_number_msg)
        phone = Phone.objects.get_phone(number)
        if phone.is_verified:
            if phone.usrid == self.current_user.pk:
                raise serializers.ValidationError(has_bind_by_self_msg)
            else:
                raise serializers.ValidationError(has_bind_by_other_msg)
        return number

    def validate(self, attrs):
        number = attrs['number']
        phone = Phone.objects.get_phone(number)
        attrs['phone'] = phone
        return attrs

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class PhoneBindSerializer(PhoneAddSerializer):
    """ 手机号绑定，验证验证码 """
    number = serializers.CharField(label='手机号', max_length=20, required=True)
    captcha = serializers.CharField(required=True, max_length=10)

    def validate(self, attrs):
        number, captcha = attrs['number'], attrs['captcha']
        phone = Phone.objects.get(number=number)
        is_ok, msg = phone.captcha_verify_for_bind(captcha, self.current_user.pk)
        if not is_ok:
            raise serializers.ValidationError(msg)
        phone.set_main()
        return attrs

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class WXPhoneBindSerializer(serializers.Serializer):
    """ 微信小程序获取手机号，不需要验证码直接绑定 """
    encrypted = serializers.CharField(required=True)
    iv = serializers.CharField(required=True)

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    def validate_encrypted(self, value):
        max_count_error_msg = f'最多只能绑定{Phone.limit}个手机号'
        phone_qs = Phone.objects.user_phone_qs(self.current_user.pk)
        if phone_qs.count() >= Phone.limit:
            raise serializers.ValidationError(max_count_error_msg)
        return value

    def validate(self, attrs):
        has_bind_msg = '手机号已被绑定'
        self_bind_msg = '已绑定过该手机号'
        invalid_number_msg = '手机号无效或暂不支持'
        try:
            skey = OAuthWechatApp.objects.get(
                usrid=self.current_user.pk,
                app_type=mc.WXAPPType.MPA,
            ).session_key
            encrypted, iv = attrs['encrypted'], attrs['iv']
            context = wx_data_decrypt(encrypted, skey, iv)
            phone = context['phoneNumber']
        except Exception as exc:
            capture_exception(exc)
            logger.exception(f'oauth_wechat_get_phone__error')
            raise serializers.ValidationError(f'授权已过期请重试')
        number, message = format_phonenumber(phone)
        if not number:
            raise serializers.ValidationError(invalid_number_msg)
        phone = Phone.objects.get_phone(number)
        if phone.usrid:
            if phone.usrid == self.current_user.pk:
                raise serializers.ValidationError(self_bind_msg)
            raise serializers.ValidationError(has_bind_msg)
        phone.user_phone_bind(self.current_user.pk)
        phone.set_main()
        return attrs

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class PhoneMainSerializer(serializers.Serializer):
    """ 设置为主手机号 """
    key = serializers.CharField(label='签名', max_length=50, required=True)

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    def validate_key(self, value):
        no_phone_error_msg = '无法获取手机号信息'
        set_main_error_msg = '设置失败，请稍后重试'
        try:
            phone_qs = Phone.objects.user_phone_qs(self.current_user.pk)
            phone = phone_qs.get(shahash=value)
            is_ok = phone.set_main()
            assert is_ok
        except Phone.DoesNotExist:
            raise serializers.ValidationError(no_phone_error_msg)
        except AssertionError:
            raise serializers.ValidationError(set_main_error_msg)
        return phone

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class PhoneLeaveSerializer(serializers.Serializer):
    """ 手机号解除绑定，发送验证码 """
    key = serializers.CharField(label='签名', max_length=50, required=True)

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    def validate_key(self, value):
        no_phone_error_msg = '无法获取手机号信息'
        is_main_error_msg = '主手机号无法解除绑定'
        try:
            phone_qs = Phone.objects.user_phone_qs(self.current_user.pk)
            phone = phone_qs.get(shahash=value)
            assert not phone.is_main
        except Phone.DoesNotExist:
            raise serializers.ValidationError(no_phone_error_msg)
        except AssertionError:
            raise serializers.ValidationError(is_main_error_msg)
        return phone

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class PhoneUnbindSerializer(PhoneLeaveSerializer):
    """ 手机号解除绑定，验证验证码 """
    captcha = serializers.CharField(required=True, max_length=10)

    def validate(self, attrs):
        phone, captcha = attrs['key'], attrs['captcha']
        is_ok, msg = phone.captcha_verify_for_unbind(captcha)
        if not is_ok:
            raise serializers.ValidationError(msg)
        attrs['phone'] = phone
        return attrs

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class IDCardImgSerializer(serializers.Serializer):
    """ 身份证识别，实名认证 """

    imgs = serializers.ListField(
        label='身份证照片',
        child=serializers.CharField(),
        min_length=2, max_length=2, required=True,
    )

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    def validate_imgs(self, value):
        no_imgs_error_msg = '无法获取身份证照片'
        is_verified_error_msg = '已实名认证过'
        usrid = self.current_user.pk
        is_verified = IDCard.objects.filter(usrid=usrid, is_valid=True).exists()
        if is_verified:
            raise serializers.ValidationError(is_verified_error_msg)
        if not (isinstance(value, list) and len(value) == 2):
            raise serializers.ValidationError(no_imgs_error_msg)
        if not all([oss_has_key(img) for img in value]):
            raise serializers.ValidationError(no_imgs_error_msg)
        img_front, img_back = value
        return img_front, img_back

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class DeviceLogoutSerializer(serializers.Serializer):
    """ 设备管理，注销登录 """

    tid = serializers.CharField(label='设备TID', required=True)

    @cached_property
    def current_user(self):
        user = self.context['request'].user
        assert isinstance(user, AuthUser)
        return user

    @cached_property
    def current_session_key(self):
        key = self.context['request'].session.session_key
        return key

    def validate_tid(self, value):
        not_exist_error_msg = '设备不存在或已注销'
        current_key_error_msg = '当前登录设备不能注销'
        usrid = self.current_user.pk
        try:
            pk = pk_hashid_decode(value)
            inst = UserDevice.objects.get(pk=pk, usrid=usrid)
        except (ValueError, UserDevice.DoesNotExist):
            raise serializers.ValidationError(not_exist_error_msg)
        if inst.key == self.current_session_key:
            raise serializers.ValidationError(current_key_error_msg)
        inst.logout(usrid, reason='user logout')
        return value

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass
