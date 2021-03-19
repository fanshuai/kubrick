import logging
from rest_framework import renderers

from server.djextend.drfapi.api_resp import APIOKResp
from server.djextend.drfapi.trace_req import trace_request


logger = logging.getLogger('kubrick.debug')


class APIJSONRenderer(renderers.JSONRenderer):

    def render(self, data, accepted_media_type=None, renderer_context=None):
        assert isinstance(data, dict), f'render_data_error {data}'
        data['_trace'] = trace_request(renderer_context['request'])
        data = data if ('_cd' in data) else APIOKResp(data=data).to_dict()
        return super().render(data, accepted_media_type, renderer_context)
