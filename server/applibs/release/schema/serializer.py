from rest_framework import serializers

from .. import models


class SymbolSerializer(serializers.ModelSerializer):
    """ 场景码列表 """
    class Meta:
        model = models.Symbol
        fields = ('symbol', 'title', 'fmt', 'tail', 'open', 'scened', 'bound')
        read_only_fields = fields

    open = serializers.ReadOnlyField(source='is_open')
    bound = serializers.ReadOnlyField(source='bound_date')


class SymbolViewSerializer(SymbolSerializer):
    """ 场景码详情 """
    class Meta:
        model = models.Symbol
        fields = (
            'symbol', 'fmt', 'tail', 'qrurl', 'views',
            'selfdom', 'title', 'bound', 'open', 'scened',
        )
        read_only_fields = fields

    selfdom = serializers.ReadOnlyField(source='get_selfdom')
    views = serializers.ReadOnlyField(source='views_count')
    qrurl = serializers.ReadOnlyField(source='qr_uri')
