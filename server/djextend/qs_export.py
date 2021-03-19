"""
Django QuerySet 导出下载

https://docs.djangoproject.com/en/3.1/howto/outputting-csv/

CSV 下载测试：
    curl -vv --raw "http://vagrant:5566/export?f=csv"
"""
import csv
import time
import json
import uuid
import logging
import openpyxl
import tempfile
import pendulum
from datetime import datetime
from collections import OrderedDict
from wsgiref.util import FileWrapper

from django.forms.models import model_to_dict, fields_for_model
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator
from django.db.models.query import QuerySet
from django.utils import timezone
from django import http

from server.constant.normal import TZCN


def formatter(v):
    if isinstance(v, datetime):
        if not timezone.is_aware(v):
            return v.isoformat()
        else:
            return pendulum.instance(v).in_tz(TZCN).isoformat()
    elif isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, cls=DjangoJSONEncoder)
    return v


class EchoRow(object):
    """
    An object that implements just the write method of the file-like interface.
    """

    @staticmethod
    def write(value):
        """
        Write the value by returning it, instead of storing in a buffer.
        """
        return value


class QSExportResponse(http.StreamingHttpResponse):
    """
    QuerySet Export 导出下载
    """

    def __init__(self, qs, output_name='', moheaders=None, is_csv=True):
        """
        :param qs: QuerySet
        :param output_name: 下载时文件名
        :param moheaders: 需要导出的字段名，为空则全部，_headers 与 HttpResponse 对象属性冲突
        :param is_csv: 是否用 csv 文件格式，csv 格斯使用生成器，不因数据量大阻塞 StreamingHttpResponse
        """
        self._qs = qs
        self._is_csv = is_csv
        self._moheaders = moheaders
        self._output_name = output_name
        assert isinstance(qs, QuerySet)
        # 大于5万使用 csv 格式
        if qs.count() > 50000:
            self._is_csv = True
        self._titles = self.get_titles()  # 获取列标题
        filename, content_type = self.filename_and_content_type()
        if self._is_csv:
            streaming_content = self.content_for_csv()
        else:
            streaming_content = self.content_for_xlsx()
        super(QSExportResponse, self).__init__(
            streaming_content=streaming_content,
            content_type=content_type,
        )
        self['Content-Disposition'] = 'attachment;filename="%s"' % filename

    def get_titles(self):
        """ 获取文件头信息 """
        model = self._qs.model
        fields = OrderedDict(((k, v.label) for k, v in fields_for_model(model).items()))
        if not self._moheaders:  # 设置默认导出字段
            self._moheaders = list(fields.keys())
        self._moheaders = ['PK'] + self._moheaders
        if not self._output_name:
            # noinspection PyProtectedMember
            self._output_name = model._meta.db_table  # 默认文件名为表名
        if self._is_csv:
            titles = list(fields.keys())  # csv 中文 Excel 乱码
        else:
            titles = ('%s(%s)' % (v, k) for k, v in fields.items())
        return tuple(['PK'] + list(titles))

    def filename_and_content_type(self):
        filename = '{on}_{ts}.{et}'.format(
            on=self._output_name, ts=int(time.time()), et=self._is_csv and 'csv' or 'xlsx'
        )
        content_type = self._is_csv and 'text/csv' or 'application/vnd.ms-excel'
        return filename, content_type

    def qs_data_generate(self):
        """
        QuerySet instance 生成器，带分页
        :return: generate
        """
        ts_s = time.time()
        assert isinstance(self._qs, QuerySet)
        yield self._titles
        count = self._qs.count()
        paginator = Paginator(self._qs, 2000)  # chunks of 2000
        num_pages = paginator.num_pages
        for page_idx in paginator.page_range:
            for instance in paginator.page(page_idx).object_list:
                inst_dic = model_to_dict(instance)
                pk = instance.pk
                opk = isinstance(pk, uuid.UUID) and pk.hex or pk
                inst_dic.update(PK=opk)
                row_info = [inst_dic.get(mh, '') for mh in self._moheaders]
                row_info = map(formatter, row_info)
                yield tuple(row_info)
            ps_progress = int(100.0 * page_idx / num_pages)
            logging.info('qs_data_generate: [{c}] {p}/{ps} {progress}% ...'.format(
                c=count, p=page_idx, ps=num_pages, progress=ps_progress
            ))
        ts_e = time.time()
        ts_use = round(ts_e - ts_s, 3)
        end_info = (
            '',
            'start_at:', pendulum.from_timestamp(ts_s).in_tz(TZCN).isoformat(),
            'finish_at:', pendulum.from_timestamp(ts_e).in_tz(TZCN).isoformat(),
            'use(s):', ts_use,
        )
        yield end_info
        logging.info('qs_data_generate: [{c}] use [{u}] all done.'.format(c=count, u=ts_use))

    def content_for_xlsx(self):
        """
        :return: generate
        """
        workbook = openpyxl.Workbook(write_only=True)
        ws = workbook.create_sheet()
        for row in self.qs_data_generate():
            ws.append(row)
        tmp_file = tempfile.TemporaryFile()
        workbook.save(tmp_file)
        tmp_file.seek(0)
        return FileWrapper(tmp_file)

    def content_for_csv(self):
        """
        :return: generate
        """
        pseudo_buffer = EchoRow()
        writer = csv.writer(pseudo_buffer)
        return (writer.writerow(row) for row in self.qs_data_generate())
