from django.urls import path

from server.applibs.billing import views


urlpatterns = [
    path('wxpay/query', views.WXPayQueryApiView.as_view(), name='bl_wxpay_query'),
    path('wxpay/charge', views.ChargeWXPayApiView.as_view(), name='bl_wxpay_charge'),
    path('wxpay/callbill', views.CallBillWXPayApiView.as_view(), name='bl_wxpay_callbill'),
    path('month/<int:year>-<int:month>', views.BillMonthDetailApiView.as_view(), name='bl_month_detail'),
    path('bill/unpaid', views.BillUnpaidApiView.as_view(), name='bl_bill_unpaid'),
]
