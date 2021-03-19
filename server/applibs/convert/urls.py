from django.urls import path

from server.applibs.convert import views


urlpatterns = [
    path('convs', views.ConversationsApiView.as_view(), name='cv_convs'),
    path('conv/<uuid:convid>', views.ConversationViewApiView.as_view(), name='cv_conv_view'),
    path('conv/<uuid:convid>/msg', views.ConversationMsgApiView.as_view(), name='cv_conv_msg'),
    path('conv/<uuid:convid>/stay', views.ConversationStayApiView.as_view(), name='cv_conv_stay'),
    path('conv/<uuid:convid>/call', views.ConversationCallApiView.as_view(), name='cv_conv_call'),
    path('conv/<uuid:convid>/block', views.ConversationBlockApiView.as_view(), name='cv_conv_block'),
    path('conv/<uuid:convid>/remark', views.ConversationRemarkApiView.as_view(), name='cv_conv_remark'),
    path('conv/<uuid:convid>/report', views.ReportRecordApiView.as_view(), name='cv_conv_report'),
    path('msg/<str:msgtid>/reach', views.MessageReachApiView.as_view(), name='cv_msg_reach'),
]
