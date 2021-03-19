"""
网页图标
"""
import logging
from django.http import HttpResponse
from django.views.generic import View

from kubrick.initialize import FAVICON_IMG

logger = logging.getLogger('kubrick.debug')


class FaviconImageView(View):
    """ 网页图标，favicon.ico  """

    img = FAVICON_IMG

    def get(self, request, *args, **kwargs):
        with open(self.img, 'rb') as img:
            content = img.read()
        content_type = 'image/png'
        logger.info(f'get_favicon_ico')
        return HttpResponse(content=content, content_type=content_type)
