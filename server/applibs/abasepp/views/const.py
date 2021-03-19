import time
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions

from kubrick.initialize import VERSION
from server.constant import mochoice as mc
from server.applibs.account.schema.serializer import UserSelfSerializer


class WPAInitApiView(APIView):
    """ 客户端应用用户状态初始化，小程序 """
    permission_classes = (permissions.AllowAny,)

    @staticmethod
    def get_origin(request):
        origin = request.META.get('HTTP_ORIGIN', '')
        return origin

    def get(self, request, *args, **kwargs):
        user = request.user
        logged = user.is_authenticated
        origin = self.get_origin(request)
        timestamp = int(time.time())
        user_dic = UserSelfSerializer(instance=user).data if logged else None
        data = dict(
            user=user_dic,
            timestamp=timestamp,
            version=VERSION,
            origin=origin,
        )
        return Response(data=data)


class WPAConstApiView(APIView):
    """ 客户端应用常量配置初始化，小程序 """
    permission_classes = (permissions.AllowAny,)

    @staticmethod
    def get(request, *args, **kwargs):
        constant = dict(
            genders=[dict(k=str(k), v=str(v)) for k, v in mc.UserGender.choices],
            reports=[dict(k=str(k), v=str(v)) for k, v in mc.ReportKind.choices],
        )
        data = dict(constant=constant)
        return Response(data=data)


class AreaListApiView(APIView):
    """ 地区列表 """
    permission_classes = (permissions.IsAuthenticated,)

    @property
    def area_list(self):
        from server.constant.areas import vant_area
        return vant_area

    def get(self, request, *args, **kwargs):
        data = dict(areas=self.area_list)
        return Response(data=data)
