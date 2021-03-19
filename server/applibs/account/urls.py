from django.urls import path

from server.applibs.account import views


urlpatterns = [
    path('login', views.LoginApiView.as_view(), name='ac_login'),
    path('logout', views.LogoutApiView.as_view(), name='ac_logout'),
    path('phones', views.PhonesApiView.as_view(), name='ac_phones'),
    path('phone/add', views.PhoneAddApiView.as_view(), name='ac_phone_add'),
    path('phone/bind', views.PhoneBindApiView.as_view(), name='ac_phone_bind'),
    path('phone/bind-wx', views.WXPhoneBindApiView.as_view(), name='ac_phone_bind_wx'),
    path('phone/main', views.PhoneMainApiView.as_view(), name='ac_phone_main'),
    path('phone/leave', views.PhoneLeaveApiView.as_view(), name='ac_phone_leave'),
    path('phone/unbind', views.PhoneUnbindApiView.as_view(), name='ac_phone_unbind'),
    path('profile', views.ProfileApiView.as_view(), name='ac_profile'),
    path('profile/bio', views.ProfileBioApiView.as_view(), name='ac_profile_bio'),
    path('qrcode', views.UserCodeApiView.as_view(), name='ac_usercode'),
    path('devices', views.DeviceListApiView.as_view(), name='ac_devices'),
    path('device/logout', views.DeviceLogoutApiView.as_view(), name='ac_device_logout'),
    path('password', views.PasswordApiView.as_view(), name='ac_password'),
    path('oauth/wx', views.WXOAuthUserInfoApiView.as_view(), name='ac_oauth_wechat'),
    path('oauth/wx-bind', views.WXOAuthUserInfoApiView.as_view(), name='ac_oauth_wxbind'),
    path('oauth/wx-code', views.WXOAuthSessionApiView.as_view(), name='ac_oauth_wxcode'),
    # path('idcard', views.IDCardImgApiView.as_view(), name='ac_idcard'),
]
