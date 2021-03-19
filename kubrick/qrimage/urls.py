from django.conf import settings
from django.urls import path, re_path
from django.views.generic import TemplateView

from server.applibs import qrimgview as qrv
from server.applibs.abasepp import views as abasepp


urlpatterns = [
    path('favicon.ico', abasepp.FaviconImageView.as_view(), name='favicon'),
    path('', TemplateView.as_view(template_name='qrimage/index.html'), name='index'),
    re_path(r'^(?P<key>[a-zA-Z]{7})-(?P<hotp>\d{6})$', qrv.QRResolveUserView.as_view()),  # 用户码页面解析
    re_path(r'^(?P<key>[a-zA-Z]{10})-(?P<hotp>\d{6})$', qrv.QRResolveSymbolView.as_view()),  # 场景码页面解析
    path('view/<str:hashed>', qrv.QRImagePageView.as_view(), name='qrimg_view'),  # 二维码页面预览
]


handler404 = TemplateView.as_view(template_name='qrimage/index.html', extra_context={'handler': 'Not Found'})

print(f'=====> DEBUG is {settings.DEBUG} ...')
