import time
import logging
from django.contrib import auth
from rest_framework import generics
from rest_framework import throttling
from rest_framework import permissions
from rest_framework.response import Response

from kubrick.initialize import VERSION
from server.djextend.drfapi.drf_throttle import ScopedThrottles
from server.applibs.account.models import OAuthWechatApp
from server.djextend.switch import token_dump
from ..schema import validator, serializer

logger = logging.getLogger('kubrick.debug')


class WXOAuthSessionApiView(generics.GenericAPIView):
    """ 微信OAuth获取登录凭证信息，登录 """
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (throttling.ScopedRateThrottle,)
    throttle_scope = ScopedThrottles.SignIn.name.lower()
    serializer_class = validator.WXCodeSessionSerializer

    def post(self, request, *args, **kwargs):
        wx_serializer = self.serializer_class(data=request.data)
        wx_serializer.is_valid(raise_exception=True)
        oauth_wxapp = wx_serializer.validated_data['oauth_wxapp']
        user = wx_serializer.validated_data['user']
        if oauth_wxapp.usrid and user.is_active:
            auth.login(request, user)
            token = token_dump(request.session.session_key)
            user_dic = serializer.UserSelfSerializer(user).data
            data = dict(user=user_dic, token=token)
        else:
            data = dict(user=None, token='')
        assert isinstance(oauth_wxapp, OAuthWechatApp)
        data.update(wxatid=oauth_wxapp.hid, version=VERSION, ts=int(time.time()))
        return Response(data=data)


class WXOAuthUserInfoApiView(generics.GenericAPIView):
    """ 微信OAuth获取用户信息，登录及绑定 """
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (throttling.ScopedRateThrottle,)
    throttle_scope = ScopedThrottles.SignIn.name.lower()
    serializer_class = validator.WXUserInfoSerializer

    def post(self, request, *args, **kwargs):
        wx_serializer = self.serializer_class(data=request.data)
        wx_serializer.is_valid(raise_exception=True)
        oauth_wx = wx_serializer.validated_data['oauth_wx']
        user = oauth_wx.user
        auth.login(request, user)
        token = token_dump(request.session.session_key)
        user_dic = serializer.UserSelfSerializer(user).data
        data = dict(user=user_dic, token=token)
        return Response(data=data)
