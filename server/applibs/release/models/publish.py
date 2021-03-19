import logging
from io import BytesIO
from django.db import models
from django.core.files.base import ContentFile
from django.utils.functional import cached_property
from sentry_sdk import capture_message

from kubrick import settings
from server.constant import mochoice as mc
from server.corelib.dealer import deal_time
from server.corelib.sequence import blaze, otpwd
from server.constant.validator import symbol_validator
from server.djextend.basemodel import BasicModel
from server.third.aliyun.oss import oss_path
from server.business import qrcode_url
from server.business import qrimg_util

logger = logging.getLogger('kubrick.debug')


class SubjectManager(models.Manager):

    def all_subject_qs(self):
        """ 所有主题项目 """
        qs = self.all()
        return qs


class Subject(BasicModel):
    """ 场景码发行主题项目 """

    class Meta:
        verbose_name = 'Subject'
        verbose_name_plural = verbose_name
        index_together = ['scene', 'designer']
        db_table = 'k_ls_subject'
        ordering = ('-pk',)

    id_sequence_start = int(1e5)

    name = models.CharField('名字', max_length=100, unique=True, null=True, default=None)
    scene = models.PositiveSmallIntegerField('场景', choices=mc.SymbolScene.choices, default=0)
    sample = models.ImageField('样品', upload_to=oss_path.subject_sample, null=True, blank=True, default=None)
    material = models.ImageField('素材', upload_to=oss_path.subject_material, null=True, blank=True, default=None)
    position = models.JSONField(
        '素材尺寸及二维码大小和坐标', blank=True, default=dict,
        help_text='SIZE:素材图片尺寸，COORDS:二维码左上角坐标，STATURE:二维码占位大小',
    )
    summary = models.CharField('摘要', max_length=200, blank=True, default='')
    designer = models.CharField('设计师', max_length=100, blank=True, default='')
    spuid = models.CharField('微信小商店SKU', max_length=20, db_index=True, blank=True, default='')
    batch = models.PositiveSmallIntegerField('发行批次', default=0)  # 32767
    activated = models.PositiveIntegerField('已激活', default=0)
    total = models.PositiveIntegerField('发行总量', default=0)
    record = models.JSONField('发行记录', default=dict)

    objects = SubjectManager()

    def __str__(self):
        return f'{self.name} <{self.pk}>'

    @property
    def rate_activated(self):
        """ 已激活比例(%) """
        try:
            desc = '{:.1f} %'.format(self.activated / self.total * 100)
        except ZeroDivisionError:
            desc = '-'
        return desc

    @property
    def publication_qs(self):
        """ 发行记录 """
        qs = Publication.objects.filter(subject_id=self.pk)
        return qs

    def publish(self, channel='', quantity=100):
        """ 发行 """
        if not self.scene:
            logger.warning(f'publish__no_scene {self.pk} {self.scene}')
            return
        batch = self.batch + 1
        record = self.record or {}
        now = deal_time.get_now_str()
        now_dt = now[:10].replace('-', '')
        channel = f'{now_dt}-{channel}' if channel else f'{now_dt}-{self.pk}-{batch}'
        context = dict(now=now, channel=channel, quantity=quantity)
        logger.info(f'publish__start {self.pk}-{batch} {context}')
        count, error = 0, 0
        while True:
            try:
                self.publication_create(batch, channel=channel)
            except Exception as exc:
                warn_msg = f'publication_create__error {self.pk} {str(exc)}'
                capture_message(warn_msg)
                logger.warning(warn_msg)
                logger.exception(exc)
                error += 1
            else:
                count += 1
            if count >= quantity:
                break
            elif error > quantity:
                warn_msg = f'publication_create__fail {self.pk} {error} {context}'
                capture_message(warn_msg)
                logger.warning(warn_msg)
                break
        count = self.publication_qs.filter(batch=batch).count()
        context.update(count=count)
        record[batch] = context
        self.batch, self.record = batch, record
        self.save(update_fields=['batch', 'record', 'updated_at'])
        if not (count == quantity):
            self.extra_log(f'publish-error-{batch}', **context)
        logger.info(f'publish__done {self.pk} {batch} {context}')
        self.chekcout()

    def publication_create(self, batch, channel=''):
        code = blaze.symbol_code_seq(self.pk)
        pub_inst = Publication.objects.create(
            symbol=code,
            scene=self.scene,
            subject_id=self.pk,
            status=mc.PublishStatus.Init,
            channel=channel,
            batch=batch,
        )
        pub_inst.qrimg_save()

    def chekcout(self):
        self.total = self.publication_qs.count()
        self.activated = self.publication_qs.filter(
            status=mc.PublishStatus.Activated.value
        ).count()
        self.save(update_fields=['total', 'activated', 'updated_at'])
        if self.sample:
            return
        self.check_sample()

    def check_sample(self):
        """ 生成样品 """
        if not self.scene == mc.SymbolScene.Vehicle:
            return
        if self.material and self.position:
            return  # TODO: 通过上传素材拼接
        inst = Publication.objects.filter(
            scene=self.scene
        ).order_by('pk').first()
        if not (isinstance(inst, Publication) and inst.qrimg):
            logger.warning(f'check_sample__no_qrimg {self.pk}')
            return
        media_path = settings.MEDIA_URL.lstrip('/').rstrip('/')
        key = f'{media_path}/{inst.qrimg.name}'
        with BytesIO() as buffer:
            img = qrimg_util.get_qrimg_shifting_symbol_default(key, base_encode=False)
            img.save(buffer, format='png', optimize=True, quality=99)
            img_file = ContentFile(buffer.getvalue())
        self.sample.save(f'sample-{self.pk}.png', img_file, save=True)
        self.extra_log('sample', sample=self.sample.url)


class PublicationManager(models.Manager):

    def get_usable_publication(self, code):
        """ 获取可用未绑定激活的记录 """
        try:
            inst = self.get(symbol=code)
            assert not (inst.usrid or inst.activated_at)
            assert inst.status == mc.PublishStatus.Prepared
        except Publication.DoesNotExist:
            logger.warning(f'get_usable_publication__not_exist {code}')
            return None
        except AssertionError as exc:
            exc_msg = f'get_usable_publication__state_error {code} {str(exc)}'
            capture_message(exc_msg)
            logger.warning(exc_msg)
            return None
        return inst


class Publication(BasicModel):
    """ 场景码主题发行记录 """

    class Meta:
        verbose_name = 'Publication'
        verbose_name_plural = verbose_name
        index_together = ['scene', 'batch', 'status']
        db_table = 'k_ls_publication'
        ordering = ('-pk',)

    subject = models.ForeignKey(
        to=Subject, verbose_name='主题',
        db_column='subject_id', db_index=True,
        db_constraint=False, on_delete=models.PROTECT,
    )
    symbol = models.CharField(
        '场景码', max_length=10, unique=True,
        help_text='只能为10位纯字母', validators=[symbol_validator],
    )
    scene = models.PositiveSmallIntegerField('场景', choices=mc.SymbolScene.choices, default=0)
    status = models.PositiveSmallIntegerField('状态', choices=mc.PublishStatus.choices, default=0)
    qrimg = models.ImageField('二维码', upload_to=oss_path.publication_qrimg, null=True, default=None)
    published_at = models.DateTimeField('发行时间', db_index=True, null=True, default=None)
    activated_at = models.DateTimeField('激活时间', db_index=True, null=True, default=None)
    channel = models.CharField('发行渠道', max_length=50, db_index=True, default='')
    usrid = models.BigIntegerField('激活绑定用户', db_index=True, default=0)
    memo = models.CharField('备忘', max_length=50, blank=True, default='')
    batch = models.PositiveSmallIntegerField('发行批次', default=0)  # 32767
    version = models.PositiveSmallIntegerField('版本', default=1)  # 32767

    objects = PublicationManager()

    @property
    def fmt(self):
        """ 格式化，大写中间有空格 """
        code = f'{self.symbol[:3]} {self.symbol[3:-4]} {self.symbol[-4:]}'.upper()
        return code

    @property
    def spuid(self):
        sid = self.subject.spuid
        return sid

    @property
    def qr_uri(self):
        """ 场景码内容 """
        uri = qrcode_url.get_qrcode_uri('page_qrimg_symbol', self.hotp_at, self.symbol)
        qruri = qrcode_url.qrurl_with_sign(uri)
        return qruri

    @property
    def scened(self):
        return self.get_scene_display()

    @property
    def hotp_at(self):
        hotp = otpwd.pyotp_hotp(self.symbol)
        code = hotp.at(self.version)
        return code

    @property
    def qrimg_url(self):
        if not self.qrimg:
            return ''
        return self.qrimg.url

    @cached_property
    def qrimg_shifting(self):
        """ 挪车码素材自动生成 """
        if not self.scene == mc.SymbolScene.Vehicle:
            return
        if self.subject.material and self.subject.position:
            return  # TODO: 通过上传素材拼接
        if not self.qrimg:
            logger.warning(f'qrimg_shifting__no_qrimg {self.symbol}')
            return
        media_path = settings.MEDIA_URL.lstrip('/').rstrip('/')
        key = f'{media_path}/{self.qrimg.name}'
        img = qrimg_util.get_qrimg_shifting_symbol_default(key)
        return img

    def qrimg_save(self):
        with BytesIO() as buffer:
            img = qrimg_util.get_symbol_qrimg_simple(self)
            img.save(buffer, format='png', optimize=True, quality=99)
            img_file = ContentFile(buffer.getvalue())
        self.qrimg.save(f'qrimg-{self.pk}.png', img_file, save=True)
        self.extra_log('qrimg', qrimg=self.qrimg_url)

    def activate(self, usrid):
        """ 场景码激活绑定 """
        if self.usrid:
            return False, f'{self.scened}已被绑定'
        if not (self.status == mc.PublishStatus.Prepared):
            return False, f'{self.scened}暂不可用'
        self.usrid = usrid
        self.activated_at = deal_time.get_now()
        self.status = mc.PublishStatus.Activated
        self.save(update_fields=['usrid', 'status', 'activated_at', 'updated_at'])
        from server.applibs.release.models import Symbol
        inst = Symbol.objects.create(
            symbol=self.symbol,
            usrid=self.usrid,
            scene=self.scene,
            status=mc.SymbolStatus.Bound,
            bound_at=self.activated_at,
            version=self.version,
        )
        return True, inst
