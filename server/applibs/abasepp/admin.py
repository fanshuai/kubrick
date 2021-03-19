import logging
from collections import OrderedDict
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType

from django_celery_beat.admin import PeriodicTaskAdmin
from django_celery_beat.models import PeriodicTask, SolarSchedule

logger = logging.getLogger('kubrick.debug')

admin.site.unregister(PeriodicTask)
admin.site.unregister(SolarSchedule)


@admin.register(ContentType)
class ContentTypeAdmin(admin.ModelAdmin):
    ordering = ('id',)
    list_display = ('id', 'app_label', 'model', 'model_class', 'model_count')
    readonly_fields = ('id', 'app_label', 'model', 'model_class', 'model_count')

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        return OrderedDict()

    @staticmethod
    def model_class(obj):
        cls = obj.model_class()
        return f'{cls.__module__}.{cls.__name__}'

    @staticmethod
    def model_count(obj):
        count = obj.model_class().objects.count()
        return count


@admin.register(PeriodicTask)
class CustomPeriodicTaskAdmin(PeriodicTaskAdmin):
    """Admin-interface for peridic tasks."""

    list_display = (
        '__str__', 'enabled', 'interval', 'start_time', 'last_run_at', 'one_off', 'total_run_count',
    )
    readonly_fields = ('last_run_at', 'date_changed', 'total_run_count')
    actions = ('enable_tasks', 'disable_tasks', 'run_tasks')
    fieldsets = (
        (None, {
            'fields': (
                'name', 'regtask', 'task', 'enabled', 'description',
                'date_changed', 'total_run_count',
            ),
            'classes': ('extrapretty', 'wide'),
        }),
        ('Schedule', {
            'fields': ('interval', 'crontab', 'solar', 'clocked',
                       'start_time', 'last_run_at', 'one_off'),
            'classes': ('extrapretty', 'wide'),
        }),
        ('Arguments', {
            'fields': ('args', 'kwargs'),
            'classes': ('extrapretty', 'wide', 'collapse', 'in'),
        }),
        ('Execution Options', {
            'fields': ('expires', 'expire_seconds', 'queue', 'exchange',
                       'routing_key', 'priority', 'headers'),
            'classes': ('extrapretty', 'wide', 'collapse', 'in'),
        }),
    )
