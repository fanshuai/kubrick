import logging
from django.contrib import auth

from rest_framework import generics
from rest_framework import throttling
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from server.djextend.drfapi.drf_throttle import ScopedThrottles
from server.applibs.account.models import UserDevice
from ..schema import validator, serializer

logger = logging.getLogger('kubrick.debug')


class LoginApiView(generics.GenericAPIView):
    """ 密码登录 """
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (throttling.ScopedRateThrottle,)
    throttle_scope = ScopedThrottles.LogIn.name.lower()
    serializer_class = validator.LoginSerializer

    def post(self, request, *args, **kwargs):
        login_serializer = self.serializer_class(data=request.data)
        login_serializer.is_valid(raise_exception=True)
        data = login_serializer.validated_data
        user = data['user']
        auth.login(request, user)
        request.session.save()
        user_dic = serializer.UserSelfSerializer(instance=user).data
        return Response(data=dict(user=user_dic))


class LogoutApiView(APIView):
    """ 退出登录 """
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (throttling.ScopedRateThrottle,)
    throttle_scope = ScopedThrottles.LogOut.name.lower()

    def get(self, request, *args, **kwargs):
        usrid = request.user.pk
        key = request.session.session_key
        try:
            inst = UserDevice.objects.get(key=key, usrid=usrid)
        except UserDevice.DoesNotExist:
            logger.warning(f'logout_device_not_exist {usrid} {key}')
        else:
            inst.logout(usrid, reason='logout')
            logger.info(f'logout_device_success {usrid} {key}')
        auth.logout(request)
        self.request.session.save()
        return Response(data={})


class PasswordApiView(generics.GenericAPIView):
    """ 设定或修改密码 """
    throttle_classes = (throttling.ScopedRateThrottle,)
    throttle_scope = ScopedThrottles.Passowrd.name.lower()
    serializer_class = validator.PasswordSerializer

    def post(self, request, *args, **kwargs):
        number_serializer = self.serializer_class(
            data=request.data,
            context={'user': request.user},
        )
        number_serializer.is_valid(raise_exception=True)
        data = number_serializer.validated_data
        data = dict(number=data['number'])
        return Response(data=data)
