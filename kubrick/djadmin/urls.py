from django.contrib import admin
from django.conf import settings
from django.urls import path, re_path, include
from rest_framework import permissions, documentation
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from kubrick.initialize import API_HOST, IS_DEV_ENV, SUPPORT_EMAIL
from kubrick.urls import silk_urlpattern, qrimg_urlpatterns
from kubrick.urls import urlpatterns as api_urlpatterns
from server.applibs.abasepp import views as abasepp
from server.applibs.abasepp.views import djadmin

admin.autodiscover()

if IS_DEV_ENV:
    docs_perms = (permissions.AllowAny,)
else:
    docs_perms = (permissions.IsAdminUser,)

schema_view = get_schema_view(
    openapi.Info(
        title='Kubrick API',
        default_version='V1',
        description='Kubrick REST 接口文档',
        terms_of_service='https://www.google.com/policies/terms/',
        contact=openapi.Contact(email=SUPPORT_EMAIL),
        license=openapi.License(name='BSD License'),
    ),
    url=API_HOST,
    public=True,
    patterns=api_urlpatterns,
    permission_classes=docs_perms,
)

urlpatterns = [
    silk_urlpattern,
    path('', admin.site.urls),
    path('doc/', include('django.contrib.admindocs.urls')),
    path('favicon.ico', abasepp.FaviconImageView.as_view(), name='favicon'),
    # #################### 二维码图片
    re_path(r'^qr-image/(?P<code>[a-z]{10})$', djadmin.PublicationQRImageView.as_view(), name='djadmin_qrimg'),
    *qrimg_urlpatterns,  # 用来URL生成和解析，具体访问在QRImage[qr.ifand.com]
]

# noinspection PyUnresolvedReferences
urlpatterns += [
    path('docs', documentation.include_docs_urls(
        title='API', description='API DOCS',
        schema_url=API_HOST, patterns=api_urlpatterns, permission_classes=docs_perms,
    )),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    # path('redoc', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

print(f'=====> DEBUG is {settings.DEBUG} ...')
