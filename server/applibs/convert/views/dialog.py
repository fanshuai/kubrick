"""
会话
"""
import logging
from django.http import Http404
from rest_framework.response import Response
from rest_framework import generics, throttling
from rest_framework.exceptions import MethodNotAllowed
from silk.profiling.profiler import silk_profile
from sentry_sdk import capture_message

from server.applibs.account.models import AuthUser
from server.applibs.outside.models import CallRecord
from server.applibs.convert.models import Contact, Conversation, Message
from server.applibs.account.schema.serializer import UserOtherSerializer
from server.djextend.drfapi.drf_throttle import ScopedThrottles
from server.corelib.hash_id import pk_hashid_encode, pk_hashid_decode
from server.voice.ytxz.ytx_const import YTX_SHOW_NUM_FMT
from ..schema import serializer, validator

logger = logging.getLogger('kubrick.debug')


class ConversationsApiView(generics.GenericAPIView):
    """ 联系人会话列表 """

    serializer_class = serializer.ContactSerializer

    def get(self, request, *args, **kwargs):
        usrid = request.user.pk
        limit = Contact.show_limit
        query = self.request.query_params.get('q') or ''
        unread = Contact.objects.user_contact_unread_count(usrid)
        contact_qs = Contact.objects.user_contact_query_qs(usrid, query=query)
        count, show_qs = contact_qs.count(), contact_qs[:limit]
        convs = self.serializer_class(show_qs, many=True).data
        data = dict(unread=unread, convs=convs, count=count, limit=limit, q=query)
        return Response(data=data)


class ConversationViewApiView(generics.GenericAPIView):
    """ 联系人会话详情 """

    serializer_class = serializer.ContactViewSerializer

    def get_contact(self, kwargs):
        try:
            convid = kwargs['convid']
            usrid = self.request.user.pk
            contact = Contact.objects.get(convid=convid, usrid=usrid)
            contact.conv_info.check_call_msg()
        except (Conversation.DoesNotExist, KeyError):
            raise Http404
        return contact

    def get(self, request, *args, **kwargs):
        contact = self.get_contact(kwargs)
        other = AuthUser.objects.get(pk=contact.touchid)
        other_dic = UserOtherSerializer(instance=other).data
        conv_dic = self.serializer_class(contact).data
        data = dict(conv=conv_dic, other=other_dic)
        return Response(data=data)


class ConversationBlockApiView(ConversationViewApiView):
    """ 会话联系人屏蔽 """

    def get(self, request, *args, **kwargs):
        raise MethodNotAllowed

    def post(self, request, *args, **kwargs):
        contact = self.get_contact(kwargs)
        block_serializer = validator.BlockSerializer(data=request.data)
        block_serializer.is_valid(raise_exception=True)
        is_block = block_serializer.validated_data['block']
        contact.set_block(is_block)
        other = AuthUser.objects.get(pk=contact.touchid)
        other_dic = UserOtherSerializer(instance=other).data
        conv_dic = self.serializer_class(contact).data
        data = dict(conv=conv_dic, other=other_dic, block=is_block)
        return Response(data=data)


class ConversationRemarkApiView(ConversationViewApiView):
    """ 会话联系人备注 """

    serializer_class = validator.RemarkSerializer

    def get(self, request, *args, **kwargs):
        raise MethodNotAllowed

    def post(self, request, *args, **kwargs):
        remark_serializer = self.serializer_class(data=request.data)
        remark_serializer.is_valid(raise_exception=True)
        remark = remark_serializer.validated_data['remark']
        contact = self.get_contact(kwargs)
        contact.up_remark(remark)
        data = dict(remark=remark)
        return Response(data=data)


class ConversationMsgApiView(ConversationViewApiView):
    """ 会话消息 """

    @staticmethod
    def check_last_msgid(convid, last_hid):
        """ 检查客户端最新消息，尝试增量更新 """
        last_hid = str(last_hid).replace('-', '')
        if not last_hid:
            return 0
        try:
            last_msg_id = pk_hashid_decode(last_hid)
            last_msg = Message.objects.get(
                pk=last_msg_id,
                convid=convid,
                is_del=False,
            )
        except (ValueError, IndexError, Message.DoesNotExist) as exc:
            wrong_msg = f'check_last_msgid__wrong {convid} {last_hid} {str(exc)}'
            capture_message(wrong_msg)
            logger.warning(wrong_msg)
            return 0
        return last_msg.pk

    def get(self, request, *args, **kwargs):
        contact = self.get_contact(kwargs)
        user = request.user
        contact.open_conv()
        conv = contact.conv_info
        last_hid = self.request.query_params.get('last', '')
        last_msg_id = self.check_last_msgid(conv.convid, last_hid)
        is_add, new_last = last_msg_id > 0, pk_hashid_encode(conv.last_id)
        msg_qs = conv.after_msg_qs(last_msg_id) if is_add else conv.show_msg_qs
        msgs = serializer.MessageSerializer(msg_qs, context={'user': user}, many=True).data
        data = dict(count=conv.count, limit=Conversation.show_limit)
        data.update(last=new_last, add=is_add, msgs=reversed(msgs))
        return Response(data=data)


class ConversationStayApiView(ConversationViewApiView):
    """ 会话，发留言信息 """

    def get(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    @silk_profile(name='发消息')
    def post(self, request, *args, **kwargs):
        contact = self.get_contact(kwargs)
        context = {'user': request.user, 'contact': contact}
        msg_serializer = validator.MsgStaySerializer(
            data=request.data, context=context,
        )
        msg_serializer.is_valid(raise_exception=True)
        msg = msg_serializer.save()
        assert isinstance(msg, Message)
        data = dict(new=msg.hid)
        return Response(data=data)


class ConversationCallApiView(ConversationViewApiView):
    """ 会话，双呼通话 """

    throttle_classes = (throttling.ScopedRateThrottle,)
    throttle_scope = ScopedThrottles.Call.name.lower()
    serializer_class = validator.MsgCallSerializer

    def get(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    @silk_profile(name='打电话')
    def post(self, request, *args, **kwargs):
        user = request.user
        contact = self.get_contact(kwargs)
        context = {'user': user, 'contact': contact}
        msg_serializer = self.serializer_class(
            data=request.data, context=context,
        )
        msg_serializer.is_valid(raise_exception=True)
        msg = msg_serializer.save()
        msg_dic = serializer.MessageSerializer(
            msg, context={'user': user},
        ).data
        data = dict(msg=msg_dic, show=YTX_SHOW_NUM_FMT)
        return Response(data=data)


class ReportRecordApiView(ConversationViewApiView):
    """ 举报滥用行为 """

    serializer_class = validator.ReportRecordSerializer

    def get(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def post(self, request, *args, **kwargs):
        contact = self.get_contact(kwargs)
        rr_serializer = self.serializer_class(
            data=request.data,
            context={'contact': contact},
        )
        rr_serializer.is_valid(raise_exception=True)
        record = rr_serializer.save()
        data = dict(offend=record.is_offend)
        return Response(data=data)


class MessageReachApiView(generics.GenericAPIView):
    """ 消息触达状态查询，双呼通话 """

    serializer_class = serializer.MessageSerializer

    def get_message(self, kwargs, ):
        try:
            usrid = self.request.user.pk
            msgid = pk_hashid_decode(kwargs['msgtid'])
            msg = Message.objects.get(pk=msgid, sender=usrid)
            assert msg.is_call, f'msg_type__error {msg.pk} {msg.msg_type}'
        except (Message.DoesNotExist, KeyError, AssertionError):
            raise Http404
        return msg

    def get(self, request, *args, **kwargs):
        """ 查询呼叫状态 """
        msg = self.get_message(kwargs)
        CallRecord.objects.msg_call_query(msg)
        rtm_resp = msg.rtm_event_call_reach()
        data = dict(res=rtm_resp)
        return Response(data=data)
