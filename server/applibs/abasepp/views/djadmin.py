"""
Djadmin
二维码图片查看等
"""
from django.http import Http404
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test

from server.applibs.release.models import Publication


class PublicationQRImageView(TemplateView):
    """ 场景码图片  """

    template_name = 'djadmin/qrimg.html'

    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        code = kwargs['code']
        try:
            inst = Publication.objects.get(symbol=code)
        except Publication.DoesNotExist:
            raise Http404
        return dict(inst=inst)
