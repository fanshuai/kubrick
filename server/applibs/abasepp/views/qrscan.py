"""
二维码识别
"""
from rest_framework.response import Response
from rest_framework import generics, permissions
from rest_framework.parsers import MultiPartParser
from django.core.files.uploadedfile import UploadedFile

from server.applibs.abasepp.schema import serializer
from server.corelib.dealer.deal_zbar import zbar_scan_by_up


class ScanQRCodeApiView(generics.GenericAPIView):
    """ 二维码识别 """

    parser_classes = (MultiPartParser,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializer.QRImgSerializer

    def post(self, request, *args, **kwargs):
        img_serializer = self.serializer_class(data=request.data)
        img_serializer.is_valid(raise_exception=True)
        img = img_serializer.validated_data['img']
        assert isinstance(img, UploadedFile)
        codes = zbar_scan_by_up(img)
        return Response(data=dict(codes=codes))
