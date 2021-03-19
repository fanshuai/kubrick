import logging
from rest_framework import serializers
from django.utils.functional import cached_property
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import UploadedFile

from server.applibs.outside import models
from server.corelib.dealer.deal_location import get_location_value
from server.applibs.outside.logic.scan_query import qrcode_resolve_parse
from server.business.qrcode_url import get_unquote_url
from server.applibs.account.models import AuthUser
from server.third.aliyun.oss import OSSDir
from server.third.aliyun import bucket_internal

logger = logging.getLogger('kubrick.debug')


class ImgUpSerializer(serializers.Serializer):
    """ 图片上传OSS """

    MAX_SIZE = 5  # 图片大小限定，MB

    img = serializers.ImageField(label='图片', required=True)

    def validate_img(self, value):
        img_error_msg = f'图片大小不能超过{self.MAX_SIZE}MB'
        try:
            assert isinstance(value, UploadedFile)
            assert value.size < self.MAX_SIZE * 1e6
        except (AttributeError, AssertionError):
            raise serializers.ValidationError(img_error_msg)
        return value

    def create(self, validated_data):
        raise PermissionDenied

    def update(self, instance, validated_data):
        raise PermissionDenied


class ImageScanSerializer(serializers.Serializer):
    """ OSS图片识别 """

    expire_time = 60 * 5  # OSS签名地址有效时间

    uri = serializers.CharField(label='图片地址', required=True)  # OSS Key
    location = serializers.JSONField(label='坐标信息', required=False)

    @cached_property
    def current_user(self):
        user = self.context['user']
        assert isinstance(user, AuthUser)
        return user

    @staticmethod
    def validate_uri(value):
        uri_error_msg = f'无法获取图片'
        if not bucket_internal.object_exists(value):
            raise serializers.ValidationError(uri_error_msg)
        return value

    @staticmethod
    def validate_location(value):
        value = get_location_value(value)
        return value

    def create(self, validated_data):
        oss_key = validated_data['uri']
        location = validated_data.get('location')
        inst = models.ImageScan.objects.image_scan_create(
            oss_key, usrid=self.current_user.pk, location=location,
        )
        return inst

    def update(self, instance, validated_data):
        raise PermissionDenied


class OSSTokenSerializer(serializers.Serializer):
    """ OSS Token，场景及图片扩展名 """

    scene = serializers.ChoiceField(choices=OSSDir.values, required=True)
    ext = serializers.ChoiceField(choices=['jpeg', 'jpg', 'png'], required=True)

    @staticmethod
    def validate_scene(value):
        scene_error_msg = f'不支持上传到该目录'
        if value not in [
            OSSDir.TmpFe.value,
            OSSDir.Avatar.value,
            OSSDir.ScanImg.value,
            OSSDir.IDCardHold.value,
            OSSDir.VehicleLicenseHold.value,
        ]:
            raise serializers.ValidationError(scene_error_msg)
        return value

    def create(self, validated_data):
        raise PermissionDenied

    def update(self, instance, validated_data):
        raise PermissionDenied


class QRQuerySerializer(serializers.Serializer):
    """ 微信扫码进入小程序解析 """

    q = serializers.CharField(label='二维码内容', required=True)
    action = serializers.CharField(label='动作', default='')

    def validate(self, attrs):
        url = get_unquote_url(attrs['q'])
        attrs['parse'] = qrcode_resolve_parse(url)
        return attrs

    def create(self, validated_data):
        raise PermissionDenied

    def update(self, instance, validated_data):
        raise PermissionDenied
