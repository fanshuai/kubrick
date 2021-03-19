import json
from django.db import models
from django.core import serializers
from django.forms import model_to_dict
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.core.serializers.json import DjangoJSONEncoder
from hashid_field import HashidAutoField

from server.corelib.dealer import deal_time
from server.corelib.safety import encrypt_dic
from server.corelib.sequence.instaflake import bid_generator
from server.corelib.hash_id import HID_MIN_LEN, HID_ALPHABET, pk_hashid_encode


def instance_model_dic(inst):
    """ Instance 字典 """
    assert isinstance(inst, models.Model)
    model_json = json.dumps(model_to_dict(inst), cls=DjangoJSONEncoder)
    model_dic = json.loads(model_json)
    # noinspection PyProtectedMember
    model_dic.update(
        db_table=inst._meta.db_table,
        app_label=inst._meta.app_label,
    )
    return model_dic


def instance_serialize_dic(inst):
    """ Instance 序列化为字典 """
    assert isinstance(inst, models.Model)
    serialize_json = serializers.serialize('json', [inst])[1:-1]
    serialize_dic = json.loads(serialize_json)
    serialize_dic.update(
        db_table=inst._meta.db_table,
        app_label=inst._meta.app_label,
    )
    return serialize_dic


class BasicModel(models.Model):
    """
    Basic Abstract Model
    """

    class Meta:
        abstract = True

    id_sequence_start = int(1e8)

    created_at = models.DateTimeField('创建时间', db_index=True, auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', db_index=True, auto_now=True)
    extra = models.JSONField('扩展数据', default=dict)

    def __str__(self):
        return f'{self.__class__.__name__} <{self.pk}>'

    @property
    def hid(self):
        assert isinstance(self.pk, int)
        return pk_hashid_encode(self.pk)

    @property
    def model_dic(self):
        dic = instance_model_dic(self)
        return dic

    @property
    def serialize_dic(self):
        """ 序列化为字典 """
        dic = instance_serialize_dic(self)
        return dic

    @property
    def created_at_min(self):
        """ 创建时间去毫秒 """
        if not self.created_at:
            return None
        min_created_at = deal_time.time_floor_ts(self.created_at)
        return min_created_at

    @property
    def updated_at_min(self):
        """ 更新时间去毫秒 """
        if not self.updated_at:
            return None
        min_updated_at = deal_time.time_floor_ts(self.updated_at)
        return min_updated_at

    @staticmethod
    def get_user(usrid=0):
        if not usrid:
            return AnonymousUser()
        from server.applibs.account.models import AuthUser
        try:
            user = AuthUser.objects.get(pk=usrid)
        except AuthUser.DoesNotExist:
            user = AnonymousUser()
        return user

    def extra_log(self, key, **kwargs):
        """ 添加扩展信息 """
        now = deal_time.get_now()
        now_ts = int(now.timestamp())
        new_key = f'log-{key}-{now_ts}'
        kwargs['_at'] = now.isoformat()
        value = json.loads(json.dumps(kwargs, cls=DjangoJSONEncoder))
        self.extra[new_key] = encrypt_dic(value)
        self.save(update_fields=['extra', 'updated_at'])


class BIDModel(models.Model):
    """
    Big ID Abstract Model
    """

    class Meta:
        abstract = True

    bid = models.BigIntegerField(primary_key=True, default=bid_generator)

    @property
    def tid(self):
        """ 外部ID，加密HashID """
        hexid = pk_hashid_encode(self.bid)
        return hexid

    def delete(self, using=None, keep_parents=False):
        raise PermissionDenied


class HashidModel(BasicModel):
    """
    Basic Abstract Hashid Model
    """

    class Meta:
        abstract = True

    id = HashidAutoField(primary_key=True, min_length=HID_MIN_LEN, alphabet=HID_ALPHABET)

    def __str__(self):
        return f'{self.__class__.__name__} <{self.oid}>'

    @property
    def oid(self):
        return self.id.id

    @property
    def hid(self):
        return str(self.id)
