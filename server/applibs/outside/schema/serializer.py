from rest_framework import serializers

from .. import models
from server.applibs.account.logic.get_cached import dialog_user_name, dialog_user_avatar


class ScanResultSerializer(serializers.ModelSerializer):
    """ 图片识别结果 """
    class Meta:
        model = models.ImageScan
        fields = (
            'result', 'convid', 'reason',
            'name', 'avatar', 'beable', 'url',
        )

    beable = serializers.ReadOnlyField(label='引导注册', source='beable_vehicle')
    url = serializers.ReadOnlyField(label='图片地址', source='oss_url')
    avatar = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    @staticmethod
    def get_name(obj):
        assert isinstance(obj, models.ImageScan)
        name = dialog_user_name(obj.contact_info.touchid)
        return name

    @staticmethod
    def get_avatar(obj):
        assert isinstance(obj, models.ImageScan)
        avatar = dialog_user_avatar(obj.contact_info.touchid)
        return avatar
