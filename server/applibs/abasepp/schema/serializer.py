from rest_framework import serializers
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import UploadedFile


class QRImgSerializer(serializers.Serializer):
    """ 二维码识别 """

    MAX_SIZE = 2  # 图片大小限定，MB

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
        return PermissionDenied
