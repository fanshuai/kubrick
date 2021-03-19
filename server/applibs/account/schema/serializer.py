from rest_framework import serializers
from django.utils.functional import cached_property

from server.third.agora.access import get_rtm_token
from .. import models


class UserSelfSerializer(serializers.ModelSerializer):
    """ 用户自己可见信息 """
    class Meta:
        model = models.AuthUser
        fields = (
            'name', 'tid', 'bio', 'code', 'codef', 'gender', 'genderd',
            'avatar', 'devices', 'symbols', 'rtoken', 'joinedAt', 'diffJoined',
        )

    tid = serializers.ReadOnlyField(label='用户HID', source='hid')
    bio = serializers.ReadOnlyField(label='个性签名', source='cached_profile.bio')
    code = serializers.ReadOnlyField(label='用户码', source='cached_usercode.code')
    codef = serializers.ReadOnlyField(label='用户码显', source='cached_usercode.fmt')
    gender = serializers.ReadOnlyField(label='性别', source='cached_profile.gender')
    genderd = serializers.ReadOnlyField(label='性别显', source='cached_profile.get_gender_display')
    avatar = serializers.ReadOnlyField(label='头像', source='cached_profile.avatar_url')
    joinedAt = serializers.ReadOnlyField(label='注册时间', source='joined_at')
    diffJoined = serializers.ReadOnlyField(label='注册时长', source='diff_joined')
    devices = serializers.ReadOnlyField(label='登录设备量', source='device_count')
    symbols = serializers.ReadOnlyField(label='场景码数量', source='symbol_count')
    rtoken = serializers.SerializerMethodField(label='RTM Token')

    @staticmethod
    def get_rtoken(obj):
        assert isinstance(obj, models.AuthUser)
        token = get_rtm_token(obj.hid)
        return token


class UserOtherSerializer(serializers.ModelSerializer):
    """ 对方可见用户信息 """
    class Meta:
        model = models.AuthUser
        fields = (
            'name', 'tid', 'avatar', 'codef', 'gender', 'genderd',
        )

    tid = serializers.ReadOnlyField(label='用户HID', source='hid')
    avatar = serializers.ReadOnlyField(label='头像', source='cached_avatar')
    codef = serializers.ReadOnlyField(label='用户码显', source='cached_usercode.fmt')
    gender = serializers.ReadOnlyField(label='性别', source='cached_profile.gender')
    genderd = serializers.ReadOnlyField(label='性别显', source='cached_profile.get_gender_display')


class PhoneSerializer(serializers.ModelSerializer):
    """ 手机号 """
    class Meta:
        model = models.Phone
        fields = ('tid', 'show', 'tail', 'key', 'main', 'fmt')

    key = serializers.ReadOnlyField(source='shahash')
    main = serializers.ReadOnlyField(source='is_main')
    fmt = serializers.ReadOnlyField(source='fmt_natl')


class UserDeviceSerializer(serializers.ModelSerializer):
    """ 登录设备信息 """
    class Meta:
        model = models.UserDevice
        fields = (
            'tid', 'type', 'name', 'signed',
            'diff', 'activated', 'current',
        )

    tid = serializers.ReadOnlyField(label='登录设备HID', source='hid')
    type = serializers.ReadOnlyField(label='应用类型', source='app_type')
    name = serializers.ReadOnlyField(label='设备名称', source='device_name')
    signed = serializers.ReadOnlyField(label='登录日期', source='signin_date')
    diff = serializers.ReadOnlyField(label='最后活跃', source='diff_activated')
    activated = serializers.ReadOnlyField(label='最后活跃时间', source='activated_at')
    current = serializers.SerializerMethodField(label='是否当前设备')

    @cached_property
    def current_session_key(self):
        session_key = self.context['key']
        return session_key

    def get_current(self, obj):
        assert isinstance(obj, models.UserDevice)
        is_current = obj.key == self.current_session_key
        return is_current


class UserCodeSerializer(serializers.ModelSerializer):
    """ 用户码 """
    class Meta:
        model = models.UserCode
        fields = ('code', 'fmt', 'vs')
        read_only_fields = ('code',)

    vs = serializers.ReadOnlyField(source='version')
