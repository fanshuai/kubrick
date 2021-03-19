"""
自定义分页

Settings:
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
"""
from rest_framework import pagination
from rest_framework.response import Response


class CustomPagination(pagination.PageNumberPagination):

    page_size = 20
    max_page_size = 500
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        has_next = self.page.has_next()
        has_prev = self.page.has_previous()
        return Response({
            'results': data,
            'pageInfo': {
                'page': self.page.number,
                'pageSize': self.page_size,
                'count': self.page.paginator.count,
                'perPage': self.page.paginator.per_page,
                'numPages': self.page.paginator.num_pages,
                'next': has_next and self.page.next_page_number() or None,
                'prev': has_prev and self.page.previous_page_number() or None,
                'index': dict(start=self.page.start_index(), end=self.page.end_index()),
                # 'hasNext': has_next, 'hasPrev': has_prev,
                # 'linkPrev': self.get_previous_link(),
                # 'linkNext': self.get_next_link(),
            },
        })
