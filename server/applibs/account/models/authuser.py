import os
import logging
from django.db import models
from django.core.files.base import ContentFile
from django.utils.functional import cached_property
from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.auth.password_validation import validate_password
from urllib.request import urlopen
from urllib.parse import urlparse

from kubrick import settings
from kubrick.initialize import DEFAULT_AVATAR_OSS
from server.djextend.basemodel import BasicModel, BIDModel
from server.corelib.dealer.deal_time import time_floor_ts, diff_humans
from server.applibs.account.logic.get_cached import dialog_user_avatar
from server.constant import areas, mochoice as mc
from server.corelib.sequence import idshift
from server.third.aliyun.oss import oss_path

logger = logging.getLogger('kubrick.debug')


class AuthUserManager(UserManager):
    use_in_migrations = True

    def create_authuser(self, name=''):
        """ 创建普通用户 """
        username = str(idshift.generate_uuid5())
        inst = self.create(name=name, username=username)
        return inst

    def _create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The given username must be set')
        username = self.model.normalize_username(username)
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff = True.')
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser = True.')
        return self._create_user(username, password, **extra_fields)


class AuthUser(AbstractUser, BasicModel, BIDModel):
    """ 用户 """

    class Meta(AbstractUser.Meta):
        swappable = 'AUTH_USER_MODEL'
        verbose_name = 'AuthUser'
        verbose_name_plural = verbose_name
        db_table = 'k_ac_authuser'
        ordering = ('-pk',)

    email = None
    groups = None
    last_name = None
    first_name = None
    user_permissions = None
    name = models.CharField('名字', max_length=50, db_index=True, default='')

    objects = AuthUserManager()

    REQUIRED_FIELDS = []

    def __str__(self):
        return f'<{self.pk}> {self.username}'

    def get_group_permissions(self, obj=None):
        return set()

    def get_all_permissions(self, obj=None):
        return set()

    def has_perm(self, perm, obj=None):
        return self.is_perm_admin

    def has_module_perms(self, app_label):
        return self.is_perm_admin

    def get_full_name(self):
        full_name = f"{self.name} <{self.username}>"
        return full_name

    def get_short_name(self):
        return self.name

    @property
    def is_perm_admin(self):
        is_admin = self.is_active and self.is_superuser
        return is_admin

    @property
    def unpaid(self):
        from server.applibs.billing.models import BillDetail
        bill_qs = BillDetail.objects.get_bill_unpaid_qs(self.pk)
        return bill_qs.count()

    @property
    def profile(self):
        inst = UserProfile.objects.get(usrid=self.pk)
        return inst

    @cached_property
    def cached_profile(self):
        return self.profile

    @property
    def usercode_info(self):
        """ 用户码 """
        from .usercode import UserCode
        inst = UserCode.objects.get(pk=self.pk)
        return inst

    @cached_property
    def cached_usercode(self):
        return self.usercode_info

    @property
    def joined_at(self):
        """ 注册时间去毫秒 """
        at = time_floor_ts(self.date_joined)
        return at

    @property
    def last_login_at(self):
        """ 最后登录时间去毫秒 """
        if not self.last_login:
            return None
        at = time_floor_ts(self.last_login)
        return at

    @property
    def is_pwd(self):
        """ 是否设定了密码 """
        is_set = bool(self.password and not self.has_usable_password())
        return is_set

    @property
    def device_count(self):
        """ 登录设备量 """
        from .devices import UserDevice
        count = UserDevice.objects.get_user_device_qs(self.pk).count()
        return count

    @property
    def symbol_count(self):
        """ 场景码数量 """
        from server.applibs.release.models import Symbol
        count = Symbol.objects.user_symbol_qs(self.pk).count()
        return count

    @property
    def diff_joined(self):
        """ 注册时长 """
        diff = diff_humans(self.date_joined)
        return diff

    @cached_property
    def cached_avatar(self):
        avatar = dialog_user_avatar(self.pk)
        return avatar

    def set_active(self, is_active: bool, operator=0):
        """ 更新有效状态 """
        self.is_active = is_active
        self.save(update_fields=['is_active', 'updated_at'])
        self.extra_log('active', active=is_active, operator=operator)

    def new_password(self, raw_password):
        """ 设置密码 """
        validate_password(raw_password, user=self)
        is_correct = self.check_password(raw_password)
        return is_correct

    def set_name(self, name: str) -> tuple:
        """ 设置名字 """
        if len(name) > 50:
            return False, '不合法'
        if name == self.name:
            return True, name
        self.name = name
        self.save(update_fields=['name', 'updated_at'])
        self.extra_log('name', name=name)
        return True, name


class UserProfile(BasicModel):
    """ 用户资料 """

    class Meta:
        verbose_name = 'UserProfile'
        verbose_name_plural = verbose_name
        index_together = ['gender', 'country', 'province', 'city']
        db_table = 'k_ac_userprofile'

    usrid = models.BigIntegerField(primary_key=True)
    avatar = models.ImageField('头像', upload_to=oss_path.profile_avatar, null=True, default=None)
    gender = models.PositiveSmallIntegerField('性别', choices=mc.UserGender.choices, default=0)
    birthday = models.DateField('生日', null=True, blank=True)
    bio = models.CharField('个性签名', max_length=100, default='')
    country = models.CharField('国家', max_length=200, default='')
    province = models.CharField('省份', max_length=200, default='')
    city = models.CharField('城市', max_length=200, default='')

    @cached_property
    def user(self):
        inst = AuthUser.objects.get(pk=self.usrid)
        return inst

    @property
    def area(self):
        """ 地区 """
        items = [self.country, self.province, self.city]
        items = [item for item in items if item]
        ret = ' '.join(items[-2:])
        return ret

    @property
    def area_code(self):
        """ 地区编码 """
        code = self.extra.get('area-code')
        return code

    @property
    def avatar_url(self):
        if not self.avatar:
            return DEFAULT_AVATAR_OSS
        return self.avatar.url

    @property
    def gender_rgb(self):
        """ 性别颜色 """
        if self.gender == mc.UserGender.Male:
            return 112, 152, 250  # 蓝色
        elif self.gender == mc.UserGender.Female:
            return 238, 136, 136  # 粉色
        return 53, 53, 53  # 灰色

    def set_bio(self, bio):
        """ 设置个性签名 """
        self.bio = bio
        self.save(update_fields=['bio', 'updated_at'])
        self.extra_log('bio', bio=bio)

    def set_avatar(self, url, compress=False):
        """ 设置头像 """
        img_file = ContentFile(urlopen(url).read())
        img_name = os.path.basename(urlparse(url).path)
        self.avatar.save(f'wxavatar-{img_name}.jpeg', img_file, save=True)
        self.extra_log('avatar', url=url, avatar=self.avatar_url)
        if not compress:
            return
        from server.applibs.account.tasks import oss_avatar_compress
        media_path = settings.MEDIA_URL.lstrip('/').rstrip('/')
        key = f'{media_path}/{self.avatar.name}'
        result = oss_avatar_compress(key)  # 同步压缩
        logger.info(f'set_avatar__compressed {self.pk} {key} {result}')

    def set_gender(self, gender):
        """ 设置名字 """
        if gender == self.gender:
            return True
        if gender not in mc.UserGender:
            return False
        self.gender = gender
        self.save(update_fields=['gender', 'updated_at'])
        self.extra_log('gender', gender=gender)
        return True

    def set_region(self, area):
        """ 设置地区，[{'code': '120000', 'name': '天津'}, None] """
        if not (isinstance(area, list) and len(area) == 2):
            return False
        province_info, city_info = area
        if any([province_info, city_info]):
            self.country = '中国'
            self.province = ''
            self.city = ''
        if isinstance(province_info, dict):
            code = province_info['code']
            province_name = province_info['name']
            if str(code).isdigit() and int(code) in areas.province_dic:
                self.extra['area-code'] = code
            if province_name in areas.province_dic.values():
                self.province = province_name
        if isinstance(city_info, dict):
            code = city_info.get('code')
            city_name = city_info.get('name')
            if str(code).isdigit() and int(code) in areas.city_dic:
                self.extra['area-code'] = code
            if city_name in areas.city_dic.values():
                self.city = city_name
        up_fields = ['country', 'province', 'city', 'extra', 'updated_at']
        self.save(update_fields=up_fields)
        self.extra_log('area', area=self.area)
        return True

    def oauth_wechat_profile_sync(self, info):
        """ OAuth微信信息同步 """
        from .oauth_wechat import OAuthWechat
        assert isinstance(info, OAuthWechat)
        self.gender = info.gender
        up_fields = ['gender', 'updated_at']
        self.city = info.city
        self.province = info.province
        self.country = info.country
        up_fields.extend(['city', 'province', 'country'])
        self.save(update_fields=up_fields)
        self.set_avatar(info.avatar)
        self.user.usercode_info.qrimg_save()  # TODO
