"""
AccessKey 管理
"""
import oss2
import logging
from dataclasses import dataclass
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.profile import region_provider

from kubrick.initialize import (
    IS_DEV_ENV, IS_PROD_ENV, ENV_PREFIX,
    ALIYUN_AK, ALIYUN_SECRET, ALIYUN_RAMUSR,
    ALIOSS_BUCKET_NAME, ALIOSS_CDN_HOST_URL,
    ALIOSS_ENDPOINT_PUBLIC, ALIOSS_ENDPOINT_INTERNAL,
)

logger = logging.getLogger('kubrick.debug')
region_provider.modify_point('Green', 'cn-hangzhou', 'green.cn-hangzhou.aliyuncs.com')

###########################
# AK 配置 #############
###########################


@dataclass
class AKConfig:
    """ AK 配置 """
    ak: str
    secret: str
    ramusr: str


ak_cfg = AKConfig(
    ak=ALIYUN_AK,
    secret=ALIYUN_SECRET,
    ramusr=ALIYUN_RAMUSR,
)

acs_client = AcsClient(
    ak=ak_cfg.ak,
    secret=ak_cfg.secret,
    timeout=8,
    connect_timeout=5,
    max_retry_time=3,
    debug=IS_DEV_ENV,
)
logger.info(f'=====> {ENV_PREFIX} aliyun_acs_client_init {ak_cfg.ramusr}')
###########################
# Bucket 配置 #############
###########################


@dataclass
class BucketConfig:
    """ Bucket 配置 """
    bucket_name: str
    endpoint_public: str
    endpoint_internal: str
    cdn_host_url: str

    @property
    def endpoint_public_url(self) -> str:
        """ EndPoint 公网地址 """
        return f'https://{self.endpoint_public}'

    @property
    def endpoint_internal_url(self) -> str:
        """ EndPoint 内网地址 """
        return f'https://{self.endpoint_internal}'

    @property
    def bucket_public_url(self) -> str:
        """ Bucket 公网地址 """
        return f'https://{self.bucket_name}.{self.endpoint_public}'


bucket_cfg = BucketConfig(
    bucket_name=ALIOSS_BUCKET_NAME,
    endpoint_public=ALIOSS_ENDPOINT_PUBLIC,
    endpoint_internal=ALIOSS_ENDPOINT_INTERNAL,
    cdn_host_url=ALIOSS_CDN_HOST_URL,
)

auth = oss2.Auth(ak_cfg.ak, ak_cfg.secret)
bucket_public = oss2.Bucket(auth, bucket_cfg.endpoint_public_url, bucket_cfg.bucket_name)
bucket_internal = oss2.Bucket(auth, bucket_cfg.endpoint_internal_url, bucket_cfg.bucket_name)

# 内网Bucket，仅生产环境或阿里云内网环境可用，一般降级为公网Bucket
bucket_internal = bucket_internal if IS_PROD_ENV else bucket_public

logger.info(f'==> {ENV_PREFIX} OSS_bucket_public: {bucket_public.bucket_name} {bucket_public.endpoint}')
logger.info(f'==> {ENV_PREFIX} OSS_bucket_internal: {bucket_internal.bucket_name} {bucket_internal.endpoint}')
