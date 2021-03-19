from django.urls import path

from server.applibs.outside import views


urlpatterns = [
    # path('scan', views.ImgScanView.as_view(), name='os_scan'),
    path('img-up', views.ImgUpView.as_view(), name='os_img_up'),
    path('oss-token', views.OSSTokenView.as_view(), name='os_oss_token'),
    path('qreview', views.QReviewView.as_view(), name='os_qreview'),
    path('contact', views.QRContactView.as_view(), name='os_contact'),
    path('qr-bind', views.QRCodeBindView.as_view(), name='os_qr_bind'),
]

