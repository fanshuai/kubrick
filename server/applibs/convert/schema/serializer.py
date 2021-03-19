import logging
from rest_framework import serializers
from django.utils.functional import cached_property

from .. import models
from server.applibs.account.models import AuthUser
from server.applibs.account.logic.get_cached import dialog_user_name, dialog_user_avatar

logger = logging.getLogger('kubrick.debug')


class ContactSerializer(serializers.ModelSerializer):
    """ 联系人 """

    class Meta:
        model = models.Contact
        fields = (
            'convid', 'block', 'unread', 'remark',
            'timer', 'memo', 'name', 'avatar',
        )
        read_only_fields = fields

    block = serializers.ReadOnlyField(label='屏蔽对方', source='is_block')
    timer = serializers.ReadOnlyField(label='最新消息时间', source='last_timer')
    memo = serializers.ReadOnlyField(label='最新消息内容', source='last_memo')
    avatar = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    @staticmethod
    def get_name(obj):
        assert isinstance(obj, models.Contact)
        name = dialog_user_name(obj.touchid)
        return name

    @staticmethod
    def get_avatar(obj):
        assert isinstance(obj, models.Contact)
        avatar = dialog_user_avatar(obj.touchid)
        return avatar


class ContactViewSerializer(ContactSerializer):
    """ 联系人详情，兼容会话信息 """

    class Meta:
        model = models.Contact
        fields = (
            'convid', 'count', 'limit', 'block', 'unread', 'more',
            'remark', 'timer', 'memo', 'name', 'avatar', 'called',
        )
        read_only_fields = fields

    count = serializers.ReadOnlyField(label='消息总量', source='conv_info.count')
    limit = serializers.ReadOnlyField(label='展示消息条数', source='conv_info.show_limit')
    called = serializers.ReadOnlyField(label='通话次数', source='conv_info.called')
    more = serializers.ReadOnlyField(label='消息总量', source='conv_info.count_more')  # TODO: RM


class MessageSerializer(serializers.ModelSerializer):
    """ 消息 """
    class Meta:
        model = models.Message
        fields = (
            'tid', 'reach', 'timer', 'timed', 'type',
            'readed', 'avatar', 'self', 'memo',
        )
        read_only_fields = fields

    timed = serializers.ReadOnlyField(source='is_timed')
    type = serializers.ReadOnlyField(source='msg_type')
    avatar = serializers.ReadOnlyField(source='sender_avatar')
    memo = serializers.ReadOnlyField(source='content')
    self = serializers.SerializerMethodField()

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    def get_self(self, obj):
        assert isinstance(obj, models.Message)
        is_yes = obj.be_self(self.current_user.pk)
        return is_yes
