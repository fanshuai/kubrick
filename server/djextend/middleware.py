import os
import json
import time
import logging

import user_agents
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.contrib.sessions.middleware import SessionMiddleware
from sentry_sdk import configure_scope, capture_message, capture_exception
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework import exceptions
from rest_framework import status


from kubrick.initialize import (
    PID, RUN_ENV_LOWER as RUN_ENV, HOST_NAME, IS_DEBUG, IS_DJADMIN,
)
from server.corelib.td_local import local
from server.djextend.drfapi import drf_const
from server.djextend.switch import token_dump, token_load
from server.djextend.drfapi.trace_req import trace_request
from server.corelib.sequence.idshift import generate_uuid5
from server.djextend.drfapi import api_resp as apr

logger = logging.getLogger('django.request')


def get_user_agents(request):
    """ UA信息 """
    user_agent_str = request.META.get('HTTP_USER_AGENT', '')
    user_agent_info = user_agents.parse(user_agent_str)
    return {'ua': user_agent_info}


def make_rest_response(data, status_code):
    """ 构造Rest Response """
    resp = Response(data=data, status=status_code)
    resp.renderer_context = {}
    resp.accepted_renderer = JSONRenderer()
    resp.accepted_media_type = JSONRenderer.media_type
    resp.render()
    return resp


class CustomMiddleware(MiddlewareMixin):

    def __init__(self, get_response=None):
        super().__init__(get_response=get_response)
        extra_dic = dict(
            settings=os.environ.get('DJANGO_SETTINGS_MODULE'),
            env=RUN_ENV, host=HOST_NAME, debug=IS_DEBUG, djadmin=IS_DJADMIN,
            pid=PID, now=timezone.now().isoformat(), c_n=self.__class__.__name__,
        )
        with configure_scope() as scope:
            for k, v in extra_dic.items():
                scope.set_extra(k, v)
        capture_message('custom_middleware_init', level='info')
        extra_str = json.dumps(extra_dic, sort_keys=True)
        logger.info(f'custom_middleware_init {extra_str}')

    @staticmethod
    def process_request(request):
        ruid = str(generate_uuid5())
        request.ruid = ruid
        request.req_start_time = time.time()
        request_id = f'{ruid}:{request.user.pk}'
        with configure_scope() as scope:
            scope.set_extra('request_id', request_id)
            scope.set_extra('usrid', request.user.pk)
            scope.set_extra('ruid', ruid)
        local.request_id = request_id  # for logger


class APIExceptionMiddleware(MiddlewareMixin):
    """
    API Exception Middleware
    """

    @staticmethod
    def process_request(request):
        if not str(request.path).startswith('/silk/'):
            return
        exc = exceptions.NotFound()
        status_code = status.HTTP_404_NOT_FOUND
        trace = trace_request(request)
        resp = JsonResponse(data=dict(
            _cd=apr.APICodes.fail.value,
            _msg=drf_const.get_code_status(code=status_code),
            _trace=trace, detail=exc.detail,
        ), status=status_code)
        return resp

    @staticmethod
    def process_response(request, response):
        if IS_DJADMIN:
            return response
        status_code = response.status_code
        if isinstance(response, Response):
            trace = response.data.get('_trace')
            if status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                resp = JsonResponse(data=dict(
                    _cd=apr.APICodes.fail.value,
                    _msg=drf_const.get_code_status(code=status_code),
                    _trace=trace, detail='请求超过了限速，请稍后重试',
                ), status=status_code)
            else:
                resp = response
        elif status_code == status.HTTP_404_NOT_FOUND:
            exc = exceptions.NotFound()
            trace = trace_request(request)
            resp = JsonResponse(data=dict(
                _cd=apr.APICodes.fail.value,
                _msg=drf_const.get_code_status(code=status_code),
                _trace=trace, detail=exc.detail,
            ), status=status_code)
        else:
            resp = response
            trace = trace_request(request)
            method, uri = request.method, request.build_absolute_uri()
            logger.info(f'middleware_response_not_api {method} {uri}')
        try:
            route = request.resolver_match.route
            route = route or request.path
        except AttributeError:
            route = request.path
        local.req_count_dic = dict(
            trace=trace, route=route,
            host=request.get_host(),
            method=request.method,
            status=resp.status_code,
            usrid=request.user.pk,
            uri=request.build_absolute_uri(),
            key=request.session.session_key,
            ua=request.META.get('HTTP_USER_AGENT', '')
        )
        return resp

    @staticmethod
    def process_exception(request, exception):
        exc = exception
        sentry = capture_exception(exc)
        request_id = getattr(local, 'request_id', None)
        method, uri = request.method, request.build_absolute_uri()
        logger.exception(f'process_exception [{request_id}] {method} {uri}', extra={
            'request': request,
        })
        if IS_DJADMIN:
            return None
        if not isinstance(exc, exceptions.APIException):
            exc = exceptions.APIException(detail=str(exc))
        status_code = exc.status_code
        is_server_error = status.is_server_error(status_code)
        resp = make_rest_response(dict(
            _cd=apr.APICodes.error.value,
            _msg=drf_const.get_code_status(code=status_code),
            _trace=trace_request(request, sentry=sentry),
            detail=is_server_error and drf_const.API_EXCEPTION or exc.detail,
        ), status_code)
        return resp


class TokenSessionMiddleware(SessionMiddleware):

    @staticmethod
    def get_header_token_session_key(request):
        """ 获取请求头中的Token """
        token = request.META.get('HTTP_X_TOKEN')
        if not token:
            token = request.META.get('HTTP_AUTHORIZATION')
            if not (isinstance(token, str) and token.startswith('Token ')):
                return None
            token = token.replace('Token ', '')
        token = token.strip()
        session_key = token_load(token)
        return session_key

    def process_request(self, request):
        header_session_key = self.get_header_token_session_key(request)
        if header_session_key:
            cookie_session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
            if cookie_session_key and cookie_session_key != header_session_key:
                logger.warning(f'session_key__cookie_to_header {cookie_session_key} > {header_session_key}')
                with configure_scope() as scope:
                    scope.set_extra('cookie_session_key', cookie_session_key)
                    scope.set_extra('header_session_key', header_session_key)
                capture_message('session_key__cookie_to_header', level='warning')
            request.COOKIES[settings.SESSION_COOKIE_NAME] = header_session_key
        setattr(request, 'csrf_processing_done', True)  # DRF Token ignore csrf
        super().process_request(request)

    def process_response(self, request, response):
        response = super().process_response(request, response)
        response['X-Token'] = token_dump(request.session.session_key)
        return response
