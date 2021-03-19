import logging

from server.corelib.td_local import local

NO_REQUEST_ID = 'none'


class RequestIDFilter(logging.Filter):

    def filter(self, record):
        record.request_id = getattr(local, 'request_id', NO_REQUEST_ID)
        return True
