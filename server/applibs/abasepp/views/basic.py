import time
import user_agents
from ipware import get_client_ip
from django.contrib import messages
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from kubrick.initialize import VERSION


class BaseApiView(APIView):
    """ 基础接口，服务监控CURL """
    permission_classes = (permissions.AllowAny,)

    @staticmethod
    def get(request, *args, **kwargs):
        timestamp = int(time.time())
        data = dict(
            appVersion=VERSION,
            timestamp=timestamp,
            detail='hello world ~',
        )
        return Response(data=data)


class DebugApiView(APIView):
    """ 调试接口，测试代码等 """
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):
        message_list = []
        message_storage = messages.get_messages(request)
        for message in message_storage:
            message_list.append(dict(type=message.tags, message=message.message))
        user = self.request.user
        logged = user.is_authenticated
        data = dict(messages=message_list, login=logged, **kwargs)
        if logged:
            from server.applibs.account.schema.serializer import UserOtherSerializer
            data['user'] = UserOtherSerializer(instance=user).data
        return Response(data=data)


class VerifyCodeApiView(APIView):
    """ 获取验证码 """
    permission_classes = (permissions.AllowAny,)

    @staticmethod
    def get(request, *args, **kwargs):
        from server.djextend import djcode
        image_str = djcode.DjangoVerifyCode(request).display(b64encode=True)
        data = dict(detail=image_str)
        return Response(data=data)


class ClientInfoApiView(APIView):
    """ 获取客户端信息 """
    permission_classes = (permissions.AllowAny,)

    @staticmethod
    def get(request, *args, **kwargs):
        user_agent_str = request.META.get('HTTP_USER_AGENT', '')
        user_agent_info = user_agents.parse(user_agent_str)
        data = dict(
            ip=get_client_ip(request),
            user_agent=user_agent_str,
            agent_parse=str(user_agent_info),
        )
        return Response(data=data)
