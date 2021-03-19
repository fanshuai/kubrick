import logging
from rest_framework import serializers
from django.utils.functional import cached_property

from server.constant import mochoice as mc
from server.applibs.account.models import AuthUser, Phone
from server.corelib.dealer.deal_string import filter_newlines
from server.applibs.convert.models import Contact, Message, ReportRecord
from server.corelib.dealer.deal_location import get_location_value

logger = logging.getLogger('kubrick.debug')


class BlockSerializer(serializers.Serializer):
    """ 屏蔽对方 """
    block = serializers.BooleanField(label='是否屏蔽', required=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class RemarkSerializer(serializers.Serializer):
    """ 设置备注 """
    remark = serializers.CharField(label='备注', default='', max_length=10, allow_blank=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class MsgStaySerializer(serializers.Serializer):
    """ 发留言消息 """
    txt = serializers.CharField(label='内容', max_length=200, required=True)
    location = serializers.JSONField(label='坐标信息', required=False)

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    @cached_property
    def current_contact(self):
        contact = self.context['contact']
        assert isinstance(contact, Contact)
        return contact

    def validate_txt(self, value):
        limit_error_msg = '对方未回复，只能连续发送三条消息'
        conv = self.current_contact.conv_info
        if conv.limit_usrid == self.current_user.pk:
            raise serializers.ValidationError(limit_error_msg)
        value = filter_newlines(value)
        return value

    @staticmethod
    def validate_location(value):
        value = get_location_value(value)
        return value

    def validate(self, attrs):
        return attrs

    def create(self, validated_data):
        location = validated_data.get('location')
        msg = Message.objects.stay_msg_add(
            self.current_contact,
            validated_data['txt'],
            location=location,
        )
        return msg

    def update(self, instance, validated_data):
        pass


class MsgCallSerializer(serializers.Serializer):
    """ 双呼匿名通话 """
    location = serializers.JSONField(label='坐标信息', required=False)

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    @cached_property
    def current_contact(self):
        contact = self.context['contact']
        assert isinstance(contact, Contact)
        return contact

    @staticmethod
    def validate_location(value):
        value = get_location_value(value)
        return value

    def validate(self, attrs):
        usrid = self.current_user.pk
        if not Phone.objects.user_phone_main(usrid):
            raise serializers.ValidationError('请先绑定手机号')
        if self.current_contact.is_block:
            block_error_msg = '你已屏蔽对方，请先取消后再呼叫'
            raise serializers.ValidationError(block_error_msg)
        if self.current_contact.is_blocked:
            blocked_error_msg = '暂时无法呼叫对方，请稍后重试'
            raise serializers.ValidationError(blocked_error_msg)
        touchid = self.current_contact.touchid
        if not Phone.objects.user_phone_main(touchid):
            raise serializers.ValidationError('对方尚未绑定手机号')
        return attrs

    def create(self, validated_data):
        location = validated_data.get('location')
        msg = Message.objects.call_msg_add(
            self.current_contact,
            location=location,
        )
        return msg

    def update(self, instance, validated_data):
        pass


class ReportRecordSerializer(serializers.Serializer):
    """ 举报 """
    kind = serializers.ChoiceField(label='类型', choices=mc.ReportKind.values)
    report = serializers.CharField(label='类型自定义', max_length=20, default='', allow_blank=True)
    offend = serializers.BooleanField(label='是否令人反感', default=False, required=False)
    offended = serializers.CharField(label='原因及感受', default='', allow_blank=True)

    @cached_property
    def current_contact(self):
        contact = self.context['contact']
        assert isinstance(contact, Contact)
        return contact

    def validate(self, attrs):
        kind = attrs['kind']
        report = attrs['report']
        kind_error_msg = '请确认举报类型输入'
        if kind == mc.ReportKind.Other.value and not report:
            raise serializers.ValidationError(kind_error_msg)
        return attrs

    def create(self, validated_data):
        inst = ReportRecord.objects.add_report_record(
            self.current_contact.usrid,
            self.current_contact.touchid,
            validated_data['kind'],
            kind_txt=validated_data['report'],
            is_offend=validated_data['offend'],
            offended=validated_data['offended'],
        )
        return inst

    def update(self, instance, validated_data):
        pass
