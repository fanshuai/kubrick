import logging
from django.db import models
from django.contrib.postgres import fields
from django.core.exceptions import PermissionDenied

from server.constant import mochoice as mc
from server.corelib.dealer import deal_time
from server.corelib.sequence import idshift
from server.third.agora import agora_rtm_send_peer
from server.corelib.hash_id import pk_hashid_encode
from server.corelib.dealer.deal_string import filter_newlines
from server.applibs.account.logic.get_cached import dialog_user_name, dialog_user_avatar
from server.djextend.basemodel import BasicModel, BIDModel

logger = logging.getLogger('kubrick.debug')


class ContactManager(models.Manager):

    def create_contact(self, convid, usrid, touchid):
        """ 联系人创建 """
        inst, is_created = self.get_or_create(
            usrid=usrid, touchid=touchid,
            defaults=dict(convid=convid),
        )
        inst.add_keyword(inst.touch_info.name)
        return inst

    def link_contact(self, usrid, touchid, symbol=''):
        """ 会话联系人关联 """
        assert 0 < (usrid != touchid) > 0, f'{usrid} {touchid}'
        conv = Conversation.objects.conversation_init([usrid, touchid], usrid, symbol=symbol)
        contact = self.create_contact(conv.convid, usrid, touchid)
        self.create_contact(conv.convid, touchid, usrid)
        return contact

    def get_exist_convid(self, usrid, touchid):
        """ 获取已存在会话ID """
        if not (usrid and touchid):
            return None
        try:
            inst = self.get(usrid=usrid, touchid=touchid)
        except Contact.DoesNotExist:
            return None
        return inst.convid

    def user_contact_unread_count(self, usrid):
        """ 获取有未读消息的会话量 """
        count = self.filter(
            usrid=usrid,
            unread__gt=0,
            is_block=False,
        ).count()
        return count

    def user_contact_query_qs(self, usrid, query=''):
        """ 用户联系人列表，含检索，前20个 """
        qs = self.filter(usrid=usrid)
        if query:
            qs = qs.filter(keywords__icontains=query)
        qs = qs.order_by('-unread', '-last_at')
        return qs


class Contact(BasicModel, BIDModel):
    """ 联系人 """

    class Meta:
        verbose_name = 'Contact'
        verbose_name_plural = verbose_name
        unique_together = ('usrid', 'touchid')
        db_table = 'k_cv_contact'
        ordering = ('-updated_at',)

    show_limit = 20  # 联系人展示记录条数

    convid = models.UUIDField('会话', db_index=True)
    usrid = models.BigIntegerField('用户', db_index=True)
    touchid = models.BigIntegerField('对方', db_index=True)
    unread = models.PositiveSmallIntegerField('未读消息量', default=0)
    read_at = models.DateTimeField('最后阅读', null=True, default=None)  # 标记已读
    last_msg = models.JSONField('最新消息内容', help_text='', default=dict)
    last_at = models.DateTimeField('最新消息时间', db_index=True, null=True, default=None)
    keywords = fields.CICharField('检索关键字', max_length=255, db_index=True, default='')
    is_block = models.BooleanField('屏蔽对方', default=False)
    remark = models.CharField('备注', max_length=50, default='')

    objects = ContactManager()

    @property
    def other_info(self):
        """ 对方联系人信息 """
        inst = self.__class__.objects.get(
            usrid=self.touchid, touchid=self.usrid
        )
        return inst

    @property
    def is_blocked(self):
        """ 是否被屏蔽 """
        is_block = self.other_info.is_block
        return is_block

    @property
    def user(self):
        inst = self.get_user(self.usrid)
        return inst

    @property
    def touch_info(self):
        inst = self.get_user(self.touchid)
        return inst

    @property
    def conv_info(self):
        inst = Conversation.objects.get(convid=self.convid)
        return inst

    @property
    def unread_msg_qs(self):
        """ 未读消息列表 """
        qs = self.conv_info.msg_qs.filter(
            read_at__isnull=True,
        ).exclude(sender=self.usrid)
        return qs

    @property
    def last_timer(self):
        """ 最新消息显示时间值 """
        if not self.last_at:
            return ''
        desc = deal_time.show_humanize_simple(self.last_at)
        return desc

    @property
    def last_memo(self):
        """ 最新消息，含称谓转换 """
        memo = self.last_msg.get('memo', '')
        return memo

    def set_block(self, is_block):
        self.is_block = is_block
        self.save(update_fields=['is_block', 'updated_at'])
        self.extra_log('block', block=self.is_block)

    def up_unread(self):
        """ 更新未读消息量 """
        self.unread = self.unread_msg_qs.count()
        self.save(update_fields=['unread', 'updated_at'])

    def open_conv(self):
        """ 打开会话 """
        self.mark_read()

    def mark_read(self):
        """ 标记已读 """
        now = deal_time.get_now()
        if self.unread == 0:
            logger.info(f'contact__marked_read {self.usrid}')
            return
        for msg in self.unread_msg_qs:
            msg.mark_read(self.usrid, now)
        self.unread, self.read_at = 0, now
        self.save(update_fields=['unread', 'read_at', 'updated_at'])
        self.rtm_event_open_conv()  # 更新不同设备未读消息量

    def rtm_event_open_conv(self):
        """ 打开会话，同步客户端，发送至RTM """
        # 1. 更新接接收者不同设备会话列表未读消息量
        # 2. 更新发送者对话框消息是否已读状态
        rtm_e = mc.LCEvent.OpenConv
        user_tid = pk_hashid_encode(self.usrid)
        touch_tid = pk_hashid_encode(self.touchid)
        content = dict(evt=rtm_e, cid=self.convid, usrtid=user_tid)
        agora_rtm_send_peer(content, [user_tid, touch_tid])

    def add_keyword(self, word):
        """ 添加索引关键词 """
        word = str(word).replace('|', '')
        word = word.replace(' ', '').strip()
        if (not word) or (word in self.keywords):
            return
        self.keywords += f'|{word}'
        self.save(update_fields=['keywords', 'updated_at'])

    def up_remark(self, remark):
        """ 修改备注 """
        self.remark = remark
        self.save(update_fields=['remark', 'updated_at'])
        self.add_keyword(remark)

    def check_last_msg(self):
        """ 冗余最新消息，用于最近联系人列表显示 """
        last_msg = self.conv_info.last_msg
        assert isinstance(last_msg, Message)
        msg_memo = last_msg.trigger_content(self.usrid)
        is_self = self.usrid == last_msg.sender
        memo = filter_newlines(msg_memo, ' ')
        self.last_msg = dict(
            memo=memo,
            self=is_self,
            id=last_msg.pk,
            by=last_msg.sender,
        )
        self.last_at = last_msg.created_at
        self.save(update_fields=['last_at', 'last_msg', 'updated_at'])


class ConversationManager(models.Manager):

    @staticmethod
    def check_convid(members):
        """ 会话ID生成，用户ID排序，UUID """
        assert isinstance(members, list)
        assert len(members) == 2
        uids = sorted(members)
        uidstr = ':'.join([str(uid) for uid in uids])
        convid = idshift.generate_name_uuid(uidstr)
        return convid

    def conversation_init(self, members, creator, symbol=''):
        """ 会话初始化 """
        attrs = dict(creator=creator)
        convid = self.check_convid(members)
        inst, _ = self.get_or_create(convid=convid, defaults=dict(
            members=members, attrs=attrs
        ))
        inst.update_symbol(symbol)
        return inst


class Conversation(BasicModel, BIDModel):
    """ 会话，仅P2P，不群聊 """
    class Meta:
        verbose_name = 'Conversation'
        verbose_name_plural = verbose_name
        db_table = 'k_cv_conversation'
        ordering = ['-last_at']

    show_limit = 20  # 展示消息条数

    convid = models.UUIDField('会话', unique=True)
    last_id = models.BigIntegerField('最新消息', db_index=True, default=0)
    last_by = models.BigIntegerField('最新消息发送者', db_index=True, default=0)
    last_at = models.DateTimeField('最新消息时间', db_index=True, null=True, default=None)
    symbol = models.CharField('场景码或用户码', max_length=10, db_index=True, default='')
    members = fields.ArrayField(
        models.BigIntegerField('用户', default=0),
        verbose_name='成员', size=2, db_index=True,
    )
    called = models.PositiveIntegerField('通话次数', default=0)  # 仅打通
    count = models.PositiveIntegerField('消息总量', default=0)
    attrs = models.JSONField('自定义属性', default=dict)

    objects = ConversationManager()

    @property
    def contact_qs(self):
        """ 会话成员 """
        qs = Contact.objects.filter(
            convid=self.convid,
        ).order_by('pk')
        return qs

    @property
    def msg_qs(self):
        """ 所有消息 """
        qs = Message.objects.filter(
            convid=self.convid,
            is_del=False,
        ).order_by('-pk')
        return qs

    @property
    def callok_msg_qs(self):
        """ 所有成功通话记录 """
        qs = self.msg_qs.filter(
            msg_type=mc.MSGType.CallMsg,
            reach=mc.CallStatus.ENDOKCall,
        ).order_by('-pk')
        return qs

    @property
    def show_msg_qs(self):
        """ 展示消息，最近20条 """
        qs = self.msg_qs[:self.show_limit]
        return qs

    def after_msg_qs(self, after):
        """ 展示消息，晚于某条记录 """
        qs = self.msg_qs.filter(pk__gt=after)
        return qs

    @property
    def msg_new(self):
        """ 最新消息 """
        msg = self.msg_qs.first()
        return msg

    @property
    def last_msg(self):
        msg = Message.objects.get(pk=self.last_id)
        return msg

    @property
    def count_more(self):
        """ 超出展示长度多少条信息 """
        count = self.count - self.show_limit
        more = count if count > 0 else 0
        return more

    @property
    def limit_usrid(self):
        """ 乒乓对话，单用户最多可连续发三条消息 """
        last_msgs = self.msg_qs.filter(
            msg_type=mc.MSGType.StayMsg,
        ).values('bid', 'sender')[:3]
        msg_ids = [msg['bid'] for msg in last_msgs]
        user_ids = [msg['sender'] for msg in last_msgs]
        # 检查总共是否少于三条消息
        if len(user_ids) < 3:
            return None
        user_ids = set(user_ids)
        # 检查最后三条消息是否由双方组成
        if not (len(user_ids) == 1):
            return None
        # 检查中间是否有过成功通话记录
        has_called = self.callok_msg_qs.filter(
            bid__gt=min(msg_ids),
            bid__lt=max(msg_ids),
            is_del=False,
        ).exists()
        if has_called:
            return None
        return user_ids.pop()

    def last_self_msg(self, sender):
        """ 自己发出的最后消息 """
        msg = self.msg_qs.filter(sender=sender).first()
        return msg

    def check_msg(self):
        """ 更新联系人消息 """
        msg = self.msg_new
        if not isinstance(msg, Message):
            return
        if self.last_id == msg.pk:
            return
        self.last_id = msg.pk
        self.last_by = msg.sender
        self.last_at = msg.created_at
        self.count = self.msg_qs.count()
        up_fields = ['last_id', 'last_by', 'last_at', 'count', 'updated_at']
        self.save(update_fields=up_fields)
        self.check_contact_msg()

    def check_contact_msg(self):
        """ 更新未读消息及最新消息 """
        for contact in self.contact_qs:
            contact.check_last_msg()
            contact.up_unread()
        logger.info(f'check_contact_msg__done {self.pk}')

    def update_symbol(self, symbol):
        """ 更新Symbol，触发消息触发 """
        if not symbol:
            return
        if self.symbol == symbol:
            return
        self.symbol = symbol
        self.save(update_fields=['symbol', 'updated_at'])
        self.extra_log('symbol', symbol=symbol)

    def check_call_msg(self):
        """ 检查通话状态，非终态 """
        from server.applibs.outside.models import CallRecord
        msg_qs = self.msg_qs.filter(
            msg_type=mc.MSGType.CallMsg,
        ).exclude(reach__in=[
            mc.CallStatus.ENDCaller,
            mc.CallStatus.ENDCalled,
            mc.CallStatus.ENDOKCall,
        ])
        count = msg_qs.count()
        if count == 0:
            logger.info(f'check_call_msg__none {self.pk}')
            self.check_msg()
            return
        deal, error = 0, 0
        for msg in msg_qs:
            try:
                CallRecord.objects.msg_call_query(msg)
                deal += 1
            except CallRecord.DoesNotExist:
                logger.warning(f'check_call_msg__no_call_record {msg.pk}')
                msg.mark_delete('无通话记录')
                error += 1
        logger.warning(f'check_call_msg__done {self.pk} {deal}/{error}/{count}')
        self.check_msg()

    def checkout_called(self):
        """ 更新通话次数 """
        self.called = self.callok_msg_qs.count()
        self.save(update_fields=['called', 'updated_at'])


class MessageManager(models.Manager):

    def _msg_create(self, **kwargs):
        """ 消息创建 """
        convid = kwargs['convid']
        sender = kwargs['sender']
        location = kwargs['location']
        conv = Conversation.objects.get(convid=convid)
        assert sender in conv.members, f'sender_error {convid} {sender}'
        kwargs['location'] = location if isinstance(location, dict) else {}
        kwargs['symbol'] = kwargs.get('symbol') or conv.symbol
        msg = self.create(**kwargs)
        msg.check_context()
        return msg

    def trigger_msg_add(self, contact, trigger, content, symbol, location=None, **kwargs):
        """ 触发消息添加 """
        assert isinstance(contact, Contact)
        assert trigger in mc.TriggerType, f'trigger_error {contact.pk} {trigger} {symbol}'
        conv_info = contact.conv_info
        msg_body = dict(trigger=trigger, **kwargs)
        last_msg = conv_info.last_self_msg(contact.usrid)
        if isinstance(last_msg, Message) and last_msg.is_trigger and last_msg.is_conv_newest:
            created_at = deal_time.time_floor_ts(last_msg.created_at)
            if deal_time.get_now().diff(created_at).in_minutes() < 30:
                return last_msg  # 30分钟内，重复触发消息，之前返回之前的消息
        read_at = deal_time.get_now()  # 触发消息，默认已读
        conv_info.update_symbol(symbol)
        msg_type = mc.MSGType.Trigger
        msg = self._msg_create(
            convid=contact.convid,
            sender=contact.usrid,
            receiver=contact.touchid,
            symbol=symbol,
            msg_type=msg_type,
            msg_body=msg_body,
            content=content,
            location=location,
            read_at=read_at,
        )
        return msg

    def stay_msg_add(self, contact, content, location=None):
        """ 留言消息 """
        assert isinstance(contact, Contact)
        msg_type = mc.MSGType.StayMsg
        msg = self._msg_create(
            convid=contact.convid,
            sender=contact.usrid,
            receiver=contact.touchid,
            content=content,
            msg_type=msg_type,
            location=location,
        )
        return msg

    def call_msg_add(self, contact, location=None):
        """ 通话消息 """
        assert isinstance(contact, Contact)
        reach = mc.CallStatus.OUTCaller
        msg_type = mc.MSGType.CallMsg
        content = '正在呼叫...'
        msg = self._msg_create(
            convid=contact.convid,
            sender=contact.usrid,
            receiver=contact.touchid,
            content=content,
            msg_type=msg_type,
            location=location,
            reach=reach,
        )
        msg.call_phone()
        return msg


class Message(BasicModel, BIDModel):
    """ 消息 """

    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = verbose_name
        index_together = ['msg_type', 'reach', 'is_del', 'is_timed']
        db_table = 'k_cv_message'
        ordering = ('-pk',)

    convid = models.UUIDField('会话', db_index=True)
    sender = models.BigIntegerField('发送者', db_index=True)
    receiver = models.BigIntegerField('接收者', db_index=True, default=0)  # 冗余
    symbol = models.CharField('场景码或用户码', max_length=10, db_index=True, default='')
    reach = models.SmallIntegerField('通话状态', choices=mc.CallStatus.choices, default=0)  # 冗余
    msg_type = models.SmallIntegerField('消息类型', choices=mc.MSGType.choices)
    msg_body = models.JSONField('上下文信息', default=dict)
    content = models.CharField('内容', max_length=255, default='')
    read_at = models.DateTimeField('阅读时间', null=True, default=None)
    is_timed = models.BooleanField('是否显示时间', default=False)
    location = models.JSONField('位置信息', default=dict)
    is_del = models.BooleanField('标记删除', default=False)

    objects = MessageManager()

    @property
    def sender_avatar(self):
        """ 发送方头像 """
        avatar = dialog_user_avatar(self.sender)
        return avatar

    @property
    def sender_remark_name(self):
        """ 发送方名字含备注，接收方视角 """
        name = dialog_user_name(self.sender)
        remark = self.contact_other.remark
        if not remark:
            return name
        return f'{name}({remark})'

    @property
    def other_remark_name(self):
        """ 对方用户名 """
        name = dialog_user_name(self.receiver)
        remark = self.contact_self.remark
        if not remark:
            return name
        return f'{name}({remark})'

    @property
    def conv_info(self):
        inst = Conversation.objects.get(convid=self.convid)
        return inst

    @property
    def contact_self(self):
        inst = Contact.objects.get(convid=self.convid, usrid=self.sender)
        return inst

    @property
    def contact_other(self):
        inst = Contact.objects.get(convid=self.convid, touchid=self.sender)
        return inst

    @property
    def diff_at(self):
        """ 过去多长时间 """
        diff = deal_time.diff_humans(self.created_at)
        return diff

    @property
    def timer(self):
        """ 显示时间值 """
        desc = deal_time.show_humanize(self.created_at)
        return desc

    @property
    def readed(self):
        """ 是否已读 """
        return bool(self.read_at)

    @property
    def is_stay(self):
        """ 是否为留言消息 """
        is_yes = self.msg_type == mc.MSGType.StayMsg
        return is_yes

    @property
    def is_call(self):
        """ 是否为通话消息 """
        is_yes = self.msg_type == mc.MSGType.CallMsg
        return is_yes

    @property
    def is_trigger(self):
        """ 是否为触发消息 """
        is_yes = self.msg_type == mc.MSGType.Trigger
        return is_yes

    @property
    def is_conv_newest(self):
        """ 是否为会话最新消息 """
        is_yes = self.conv_info.last_id == self.pk
        return is_yes

    def be_self(self, usrid):
        """ 是否是自己 """
        is_yes = self.sender == usrid
        return is_yes

    def trigger_content(self, usrid):
        """ 触发消息添加称谓，EG: [对方]通过扫描... """
        if not self.is_trigger:
            return self.content
        is_self = self.be_self(usrid)
        if is_self:
            txt = f'我{self.content}'
        else:
            txt = f'对方{self.content}'
        return txt

    def rtm_event_new_msg(self):
        """ 发送至RTM """
        rtm_e = mc.LCEvent.NewMessage
        content = dict(
            type=self.msg_type, evt=rtm_e,
            mid=self.hid, cid=self.convid,
        )
        # 发送方靠页面回退来触发更新新消息
        # sender_tid = pk_hashid_encode(self.sender)
        receiver_tid = pk_hashid_encode(self.receiver)
        agora_rtm_send_peer(content, [receiver_tid])

    def rtm_event_call_reach(self):
        """ 通话触达，同步客户端，发送至RTM """
        if not self.is_call:
            return
        self.refresh_from_db()
        rtm_e = mc.LCEvent.ReachCall
        content = dict(
            type=self.msg_type, evt=rtm_e,
            mid=self.hid, cid=self.convid,
            reachd=self.get_reach_display(),
            reach=self.reach, summary=self.content,
        )
        sender_tid = pk_hashid_encode(self.sender)
        receiver_tid = pk_hashid_encode(self.receiver)
        agora_rtm_send_peer(content, [sender_tid, receiver_tid])
        return content

    def rtm_event_bill_reach(self, bill_hid):
        """ 通话账单推送，同步客户端，发送至RTM """
        if not self.is_call:
            return
        rtm_e = mc.LCEvent.BillPush
        content = dict(
            type=self.msg_type, evt=rtm_e,
            mid=self.hid, cid=self.convid,
            reach=self.reach, hid=bill_hid,
        )
        sender_tid = pk_hashid_encode(self.sender)
        agora_rtm_send_peer(content, [sender_tid])
        return content

    def check_context(self):
        """ 消息创建后，更新坐标、及用户最新消息 """
        # 消息列表是否显示时间：10分钟内未显示过时间
        created = deal_time.time_floor_ts(self.created_at)
        is_exists_timed = self.conv_info.msg_qs.filter(
            convid=self.convid, pk__lt=self.pk, is_timed=True,
            created_at__gte=created.add(minutes=-10),
        ).exists()
        self.is_timed = not is_exists_timed
        self.save(update_fields=['is_timed', 'updated_at'])
        self.conv_info.check_msg()
        self.rtm_event_new_msg()

    def mark_read(self, usrid, dt):
        if self.read_at:
            return
        if self.sender == usrid:
            return
        self.read_at = dt
        up_fields = ['read_at', 'updated_at']
        self.save(update_fields=up_fields)

    def mark_delete(self, memo=''):
        """ 标记删除 """
        if self.is_del:
            return
        self.is_del = True
        self.save(update_fields=['is_del', 'updated_at'])
        now = deal_time.get_now()
        self.extra_log('del', pk=self.pk, now=now, memo=memo)

    def delete(self, *args, **kwargs):
        raise PermissionDenied

    def call_phone(self):
        """ 拨打双呼匿名通话 """
        assert self.is_call
        from server.applibs.outside.models import CallRecord
        call = CallRecord.objects.msg_call_phone(self)
        return call

    def sms_remind(self):
        """ 发送短信提醒，触达用户召回 """
        if self.is_del:
            return False, f'消息已删除: {self.pk}'
        if self.read_at:
            return False, f'消息已读: {self.pk} {self.read_at}'
        if self.is_call and (self.reach != mc.CallStatus.ENDCalled):
            return False, f'通话状态非[暂未接通]: {self.pk} {self.reach}'
        from server.applibs.account.models import Phone
        from server.applibs.outside.models import SmsRecord, CallRecord
        if self.is_stay:
            scene = mc.SMSNoticeScene.MSGUnread
            touch_at = self.created_at
        elif self.is_call:
            scene = mc.SMSNoticeScene.MSGMissed
            record = CallRecord.objects.get(msgid=self.pk)
            touch_at = record.callers_at or self.created_at
        else:
            logger.warning(f'sms_remind__msg_type_wrong {self.pk}')
            return False, f'消息类型错误: {self.pk} {self.msg_type}'
        diff_touch = deal_time.diff_humans(touch_at)
        params = dict(name=self.sender_remark_name, diff=diff_touch)
        phone = Phone.objects.user_phone_main(self.receiver)
        if not isinstance(phone, Phone):
            logger.warning(f'sms_remind__phone_not_exist {self.receiver}')
            return False, f'接收者无手机号: {self.pk} {self.receiver}'
        is_succ, reason = SmsRecord.objects.sms_send__msg_remind(
            scene, phone.number, params,
            self.sender, self.receiver, self.pk,
        )
        return is_succ, reason

    def up_call_reach(self, status, content):
        """ 更新通话触达状态 """
        assert self.msg_type == mc.MSGType.CallMsg, self.msg_type
        self.reach, self.content = status, content
        self.is_del = status == mc.CallStatus.ENDCaller  # 取消呼叫标记删除消息
        self.save(update_fields=['reach', 'content', 'is_del', 'updated_at'])
        self.extra_log('reach', reach=self.reach)
        if self.reach == mc.CallStatus.ENDOKCall:
            self.conv_info.checkout_called()
        elif self.is_del:  # 标记删除更新会话信息
            self.conv_info.check_msg()
        # 通话消息，消息内容通话状态更新
        self.conv_info.check_contact_msg()
        self.rtm_event_call_reach()
