"""
kubrick URL Configuration
https://docs.djangoproject.com/en/3.1/topics/http/urls/
"""
from django.urls import path, re_path, include

from server.applibs import callback
from server.applibs.abasepp import views as abasepp
from server.applibs import qrimgview


# https://pypi.org/project/django-silk/
silk_urlpattern = path('silk/', include('silk.urls', namespace='silk'))  # Profiling


# ########## 用来URL生成和解析，具体访问在QRImage[qr.ifand.com]
qrimg_urlpatterns = [
    # ##### 用户码内容
    re_path(
        r'^u/(?P<key>[a-zA-Z]{7})/(?P<hotp>\d{6})/(?P<ts>\d{10})$',
        qrimgview.QRIMGMockRedirectView.as_view(),
        name='page_qr_user',
    ),  # 旧，会重定向至新
    re_path(
        r'^(?P<key>[a-zA-Z]{7})-(?P<hotp>\d{6})$',
        qrimgview.QRIMGMockRedirectView.as_view(),
        name='page_qrimg_user',
    ),  # 新
    # ##### 场景码内容
    re_path(
        r'^s/(?P<key>[a-zA-Z]{10})/(?P<hotp>\d{6})/(?P<ts>\d{10})$',
        qrimgview.QRIMGMockRedirectView.as_view(),
        name='page_qr_symbol',
    ),  # 旧，会重定向至新
    re_path(
        r'^(?P<key>[a-zA-Z]{10})-(?P<hotp>\d{6})$',
        qrimgview.QRIMGMockRedirectView.as_view(),
        name='page_qrimg_symbol',
    ),  # 新
]

urlpatterns = [
    silk_urlpattern,  # Profiling
    *qrimg_urlpatterns,  # 与 Djadmin 共用
    path('favicon.ico', abasepp.FaviconImageView.as_view(), name='favicon'),
    # ##########  通用 API
    path('', abasepp.BaseApiView.as_view(), name='api_base'),
    path('qr-scan', abasepp.ScanQRCodeApiView.as_view(), name='qr_scan'),
    path('debug/<path:path>', abasepp.DebugApiView.as_view(), name='api_debug'),
    path('verifycode', abasepp.VerifyCodeApiView.as_view(), name='api_verifycode'),
    path('client-info', abasepp.ClientInfoApiView.as_view(), name='api_client_info'),
    # path('area-list', abasepp.AreaListApiView.as_view(), name='api_area_list'),
    path('wpa-init', abasepp.WPAInitApiView.as_view(), name='api_wpa_init'),
    path('wpa-const', abasepp.WPAConstApiView.as_view(), name='api_wpa_const'),
    #####################
    path('account/', include('server.applibs.account.urls')),
    path('billing/', include('server.applibs.billing.urls')),
    path('outside/', include('server.applibs.outside.urls')),
    path('release/', include('server.applibs.release.urls')),
    path('convert/', include('server.applibs.convert.urls')),
    # ##########  第三方回调 API
    path('cb/ytx', callback.YTXCallbackView.as_view(), name='cb_ytx'),
    path('cb/wxpay', callback.WXPayCallbackView.as_view(), name='cb_wxpay'),
]
