""" OSS存储路径 """
import os
from enum import unique
from dataclasses import dataclass
from django.db.models import TextChoices

from server.corelib.sequence import idshift
from server.corelib.dealer.deal_time import get_now


@dataclass
class OSSkey:
    """ OSSkey 信息 """
    key: str
    name: str
    updir: str


@unique
class OSSDir(TextChoices):
    """ 不同场景对应OSS目录 """
    TmpBe = '_tmpbe', '临时文件'  # 服务端
    TmpFe = '_tmpfe', '临时文件'  # 客户端
    ScanImg = '_scan', '拍一拍'  # 图片识别
    VehicleLicenseHold = '_hold/vehicle', '行驶证(待认证)'
    VehicleLicense = 'vehicle', '行驶证'
    IDCardHold = '_hold/idcard', '身份证(待认证)'
    IDCard = 'idcard', '身份证'
    Avatar = 'avatar', '头像'
    #########
    UserCodeQRImg = 'uqrimg', '用户二维码'
    PublicationQRImg = 'publication', '场景码二维码'
    SubjectMaterial = 'subject-material', '主题素材'
    SubjectSample = 'subject-sample', '主题样品'


def get_oss_key(scene, filename, instid):
    """ 根据场景获取OSS路径 """
    now = get_now()
    prefix = now.format('HHmm')
    today = now.format('YYYYMMDD')
    upload_dir = f'{scene}/{today}'
    name, ext = os.path.splitext(filename)
    uuid_key = idshift.generate_uuid5().hex[:8]
    name_key = idshift.generate_name_uuid(name).hex[-6:]
    instid = str(instid or f'none_{now.second}').lower()
    assert isinstance(scene, str) and scene in OSSDir, f'{scene}'
    new_name = f'{prefix}-{name_key}-{uuid_key}-{instid}{ext}'
    key = f'{upload_dir}/{new_name}'
    oss_key = OSSkey(key=key, name=new_name, updir=upload_dir)
    return oss_key


def profile_avatar(instance, filename):
    """ 用户资料 头像 """
    from server.applibs.account.models import UserProfile
    assert isinstance(instance, UserProfile), type(instance).__name__
    return get_oss_key(OSSDir.Avatar, filename, instance.hid).key


def usercode_qrimg(instance, filename):
    """ 用户码 二维码 """
    from server.applibs.account.models import UserCode
    assert isinstance(instance, UserCode), type(instance).__name__
    uuid_key = idshift.generate_uuid5()
    upload_dir = OSSDir.UserCodeQRImg.value
    name, ext = os.path.splitext(filename)
    msg = f'{instance.hid}-{instance.hotp_at}-{name}'
    hash_key = idshift.hmac_hash(uuid_key, msg)[-20:]
    key = f'{upload_dir}/{instance.code}-{hash_key}{ext}'
    return key


def publication_qrimg(instance, filename):
    """ 场景码 主题发行记录 二维码 """
    from server.applibs.release.models import Publication
    assert isinstance(instance, Publication), type(instance).__name__
    upload_dir = OSSDir.PublicationQRImg.value
    name, ext = os.path.splitext(filename)
    msg = f'{instance.hid}-{instance.hotp_at}-{name}'
    uuid_key = idshift.generate_uuid5()
    hash_key = idshift.hmac_hash(uuid_key, msg)[-16:]
    key = f'{upload_dir}/{instance.symbol}-{hash_key}{ext}'
    return key


def subject_material(instance, filename):
    """ 场景码发行主题 素材 """
    from server.applibs.release.models import Subject
    assert isinstance(instance, Subject), type(instance).__name__
    return get_oss_key(OSSDir.SubjectMaterial, filename, instance.hid).key


def subject_sample(instance, filename):
    """ 场景码发行主题 样品 """
    from server.applibs.release.models import Subject
    assert isinstance(instance, Subject), type(instance).__name__
    return get_oss_key(OSSDir.SubjectSample, filename, instance.hid).key
