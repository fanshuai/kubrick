from django.urls import path, re_path

from server.applibs.release import views
from server.applibs.release.views import SymbolStatusApiView as StatusView


urlpatterns = [
    path('symbols', views.SymbolsApiView.as_view(), name='ls_symbols'),
    re_path(r'^symbol/(?P<symbol>[a-z]{10})$', views.SymbolViewApiView.as_view(), name='ls_symbol_view'),
    re_path(r'^symbol/(?P<symbol>[a-z]{10})/title$', views.SymbolTitleApiView.as_view(), name='ls_symbol_title'),
    re_path(r'^symbol/(?P<symbol>[a-z]{10})/selfdom$', views.SymbolSelfdomApiView.as_view(), name='ls_symbol_selfdom'),
    re_path(r'^symbol/(?P<symbol>[a-z]{10})/(?P<status>open|close)$', StatusView.as_view(), name='ls_symbol_status'),
    re_path(r'^symbol/(?P<symbol>[a-z]{10})/leave$', views.SymbolLeaveApiView.as_view(), name='ls_symbol_leave'),
    re_path(r'^symbol/(?P<symbol>[a-z]{10})/unbind$', views.SymbolUnbindApiView.as_view(), name='ls_symbol_unbind'),
    # path('vehicle/bind', views.VehicleBindApiView.as_view(), name='ls_vehicle_bind'),
]
