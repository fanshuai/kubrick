from dataclasses import asdict
from rest_framework.response import Response
from rest_framework import generics, permissions

from server.djextend.drfapi import api_resp as apr
from server.applibs.outside.logic.scan_query import QRParse, QRQuery, qrcode_review_query
from server.applibs.convert.logic.trigger_conv import qrcode_trigger, qrcode_bind
from ..schema import validator, serializer


class ImgScanView(generics.GenericAPIView):
    """ OSS图片识别 """

    serializer_class = validator.ImageScanSerializer

    def post(self, request, *args, **kwargs):
        img_serializer = self.serializer_class(
            data=request.data,
            context={'user': request.user},
        )
        img_serializer.is_valid(raise_exception=True)
        inst = img_serializer.save()
        data = serializer.ScanResultSerializer(inst).data
        return Response(data=data)


class QReviewView(generics.GenericAPIView):
    """ 扫码内容预览 """

    permission_classes = (permissions.AllowAny,)
    serializer_class = validator.QRQuerySerializer

    def post(self, request, *args, **kwargs):
        user = request.user
        usrid = user.pk
        logged = user.is_authenticated
        q_serializer = self.serializer_class(
            data=request.data,
        )
        q_serializer.is_valid(raise_exception=True)
        qr_parse = q_serializer.validated_data['parse']
        assert isinstance(qr_parse, QRParse)
        if not qr_parse.is_ok:
            result = QRQuery(logged=logged, reason=qr_parse.reason)
            data = dict(result=asdict(result))
            return Response(data=data)
        qr_query = qrcode_review_query(qr_parse, usrid)
        if not qr_query.is_ok:
            result = QRQuery(logged=logged, reason=qr_query.reason)
            data = dict(result=asdict(result))
            return Response(data=data)
        data = dict(result=asdict(qr_query))
        return Response(data=data)


class QRContactView(generics.GenericAPIView):
    """ 扫码后会话建立 """

    serializer_class = validator.QRQuerySerializer

    def post(self, request, *args, **kwargs):
        usrid = request.user.pk
        q_serializer = self.serializer_class(
            data=request.data,
        )
        q_serializer.is_valid(raise_exception=True)
        action = q_serializer.validated_data['action']
        qr_parse = q_serializer.validated_data['parse']
        assert isinstance(qr_parse, QRParse)
        if not qr_parse.is_ok:
            api_resp = apr.APIFailResp(_msg=qr_parse.reason, data={})
            return Response(data=api_resp.to_dict())
        q_dic = asdict(qr_parse)
        is_ok, resp = qrcode_trigger(usrid, q_dic)
        if is_ok:
            data = dict(convid=resp.convid, action=action)
            api_resp = apr.APIOKResp(data=data)
        else:
            api_resp = apr.APIFailResp(_msg=resp, data={})
        return Response(data=api_resp.to_dict())


class QRCodeBindView(generics.GenericAPIView):
    """ 场景码扫码绑定 """

    serializer_class = validator.QRQuerySerializer

    def post(self, request, *args, **kwargs):
        usrid = request.user.pk
        q_serializer = self.serializer_class(
            data=request.data,
        )
        q_serializer.is_valid(raise_exception=True)
        qr_parse = q_serializer.validated_data['parse']
        assert isinstance(qr_parse, QRParse)
        if not qr_parse.is_ok:
            api_resp = apr.APIFailResp(_msg=qr_parse.reason, data={})
            return Response(data=api_resp.to_dict())
        q_dic = asdict(qr_parse)
        is_ok, resp = qrcode_bind(usrid, q_dic)
        if is_ok:
            data = dict(fmt=resp.fmt, symbol=resp.symbol)
            api_resp = apr.APIOKResp(data=data)
        else:
            api_resp = apr.APIFailResp(_msg=resp, data={})
        return Response(data=api_resp.to_dict())
