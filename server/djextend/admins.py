import json
from django.contrib import admin
from django.utils.safestring import mark_safe
from pygments.formatters.html import HtmlFormatter
from pygments.lexers.data import JsonLexer
from pygments import highlight

from server.corelib.safety import decrypt_dic


def json_format_html(data: dict) -> str:
    response = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)
    response = highlight(response, JsonLexer(), HtmlFormatter(style='default'))
    return mark_safe(response)


class ReadonlyAdmin(admin.ModelAdmin):

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def extra_json(self, obj):
        extra = getattr(obj, 'extra', {})
        return json_format_html(decrypt_dic(extra))

    extra_json.short_description = '扩展数据'
