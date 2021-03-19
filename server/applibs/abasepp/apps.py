import logging
from django.db import connection
from django.apps import AppConfig
from django.db.utils import ProgrammingError
from django.core.signals import request_finished
from django.db.models.signals import post_migrate
from sentry_sdk import configure_scope, capture_message, capture_exception

from kubrick.initialize import IS_DJADMIN
from server.constant.djalias import DBAlias

logger = logging.getLogger('kubrick.debug')
db_default = DBAlias.Default.value


class AbaseppConfig(AppConfig):
    name = 'server.applibs.abasepp'
    verbose_name = 'Abasepp App'

    def ready(self):
        from django.contrib.contenttypes.management import create_contenttypes
        post_migrate.disconnect(create_contenttypes)
        post_migrate.disconnect(
            dispatch_uid='django.contrib.auth.management.create_permissions'
        )
        post_migrate.connect(idseq_update_content_type_handler)
        post_migrate.connect(create_contenttypes)
        post_migrate.connect(idseq_update_others_handler)
        if IS_DJADMIN:
            logger.info(f'signals__request_finished_handler__djadmin_ignore')
            return
        request_finished.connect(request_finished_handler)


def idseq_update_content_type_handler(**kwargs):
    """
    Post migrate id seq update for ContentType
    """
    from django.contrib.admin.apps import AdminConfig
    from django.contrib.contenttypes.models import ContentType
    if not isinstance(kwargs.get('sender'), AdminConfig):
        return  # Only with AdminConfig, INSTALLED_APPS First
    count = ContentType.objects.using(db_default).count()
    if count > 0:
        logger.info(f'idseq_update_content_type_handler__has_done')
        return  # only run at first migrate
    start, increment = 10000, 5
    seq = f'django_content_type_id_seq'
    with connection.cursor() as cursor:  # noinspection SqlNoDataSourceInspection
        cursor.execute(f'ALTER SEQUENCE {seq} RESTART WITH {start} INCREMENT {increment};')
        logger.info(f'idseq_update_content_type_handler__success start: {start} increment: {increment}')
    logger.info(f'idseq_update_content_type_handler__connection_closed')


def idseq_update_others_handler(**kwargs):
    """
    Post migrate id seq update for Others
    """
    from django_celery_beat.apps import BeatConfig
    from django.contrib.contenttypes.models import ContentType
    if not isinstance(kwargs.get('sender'), BeatConfig):
        return  # Only with RavenConfig, INSTALLED_APPS Last
    content_type_qs = ContentType.objects.using(db_default).exclude(
        app_label__in=['contenttypes', 'sessions']
    )
    content_type_count = content_type_qs.count()
    logger.info(f'idseq_update_others_handler__content_type count: {content_type_count}')
    with connection.cursor() as cursor:
        alter_count = 0
        for content_type in content_type_qs:
            logger.info(f'content_type: {content_type.id} {content_type.app_label} {content_type.model}')
            model = content_type.model_class()
            if not model:
                logger.info(f'idseq_update_others_handler__app_not_install_continue {content_type.model}')
                continue
            model_name = model.__name__
            if not hasattr(model, 'id'):
                logger.info(f'idseq_update_others_handler__no_id_field {model_name}')
                continue  # 无自增ID主键
            start = getattr(model, 'id_sequence_start', 1000000)
            assert isinstance(start, int) and start > 0, f'get_start_error {model_name}'
            # noinspection PyProtectedMember
            table = model._meta.db_table
            try:
                obj_count = model.objects.using(db_default).count()
            except ProgrammingError as exc:
                logger.info(f'idseq_update_others_handler__count_error {model_name} {type(exc).__name__} !!')
                continue
            if obj_count > 0:
                last_id = model.objects.using(db_default).order_by('id').last().id
                logger.info(f'idseq_update_others_handler__not_empty {model_name}: {obj_count} > {last_id}')
                continue  # 只修改无数据 Model 的 seq 起始值
            seq = f'{table}_id_seq'
            try:  # noinspection SqlNoDataSourceInspection
                cursor.execute(f'ALTER SEQUENCE {seq} RESTART WITH {start};')
            except Exception as exc:
                logger.info(f'idseq_update_others_handler__error {model_name}: {seq} {str(exc)}')
            else:
                logger.info(f'idseq_update_others_handler__success {model_name}: {seq} start with {start}')
                alter_count += 1
        logger.info(f'idseq_update_others_handler__all_done count: {alter_count}')
    logger.info(f'idseq_update_others_handler__connection_closed')


def request_finished_handler(**kwargs):
    from server.corelib.td_local import local
    from server.applibs.monitor.models import APIReqCount
    from server.applibs.account.models import UserDevice
    req_dic = getattr(local, 'req_count_dic', None)
    if not (req_dic and isinstance(req_dic, dict)):
        logger.info(f'request_finished_handler__no_req_dic')
        return kwargs
    try:
        APIReqCount.objects.req_count_increase(req_dic)
    except Exception as exc:
        logger.info(f'req_count_increase__error {req_dic}')
        logger.exception(str(exc))
        capture_exception(exc)
    try:
        UserDevice.objects.deviceinfo_update(req_dic)
    except Exception as exc:
        logger.info(f'deviceinfo_update__error {req_dic}')
        logger.exception(str(exc))
        capture_exception(exc)
    try:
        del local.req_count_dic
    except AttributeError:
        capture_message('del_req_count_dic__error', level='warning')
        logger.warning(f'del_req_count_dic__error {req_dic}')
    req_id = getattr(local, 'request_id', None)
    try:
        del local.request_id
    except AttributeError:
        capture_message('del_local_request_id__error', level='warning')
        logger.warning(f'del_local_request_id__error {req_dic}')
    with configure_scope() as scope:
        scope.clear()
    logger.info(f'request_finished_handler__done {req_id}')
