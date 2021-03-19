from rest_framework import generics
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser

from server.third.aliyun.oss import fe_oss_token, be_image_upload
from ..schema import validator


class ImgUpView(generics.GenericAPIView):
    """ 图片上传OSS """

    parser_classes = (MultiPartParser,)
    serializer_class = validator.ImgUpSerializer

    def post(self, request, *args, **kwargs):
        img_serializer = self.serializer_class(data=request.data)
        img_serializer.is_valid(raise_exception=True)
        img = img_serializer.validated_data['img']
        result = be_image_upload(img, usrid=request.user.pk)
        return Response(data=result)


class OSSTokenView(generics.GenericAPIView):
    """ 获取客户端OSS上传Token """

    serializer_class = validator.OSSTokenSerializer

    def post(self, request, *args, **kwargs):
        usrid = self.request.user.pk
        oss_serializer = self.serializer_class(
            data=request.data,
            context={'user': request.user},
        )
        oss_serializer.is_valid(raise_exception=True)
        ext = oss_serializer.validated_data['ext']
        scene = oss_serializer.validated_data['scene']
        result = fe_oss_token(scene, ext, usrid)
        return Response(data=result)
