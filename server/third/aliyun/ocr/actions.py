"""
OCR 车牌号识别
https://help.aliyun.com/document_detail/53435.html
https://help.aliyun.com/document_detail/87122.html
流量包成本：810 / 500000 * 11.1 = 0.017982
"""
import json
import logging
from sentry_sdk import capture_exception
from aliyunsdkgreen.request.v20180509 import ImageSyncScanRequest

from server.constant import mochoice as mc
from server.third.aliyun import AliReqAction

logger = logging.getLogger('kubrick.api')

ocr_type_cards = (
    (mc.OCRType.QRCode, ('', 'qrcodeData')),
    (mc.OCRType.IDCardBack, ('id-card-back', 'idCardInfo')),
    (mc.OCRType.IDCardFront, ('id-card-front', 'idCardInfo')),
    (mc.OCRType.VehicleNum, ('vehicle-num', 'vehicleNumInfo')),
    (mc.OCRType.VehicleLicenseFront, ('vehicle-license-front', 'vehicleLicenseFrontInfo')),
)

ocr_type_cards_dic = dict(ocr_type_cards)


def ocr_req(oss_url, data_id, card, scenes=None):
    """ OCR请求 """
    if not scenes:
        scenes = ['ocr']
    task = {
        'dataId': data_id,
        'url': oss_url,
    }
    params = {
        'tasks': [task],
        'scenes': scenes,
        'extras': {'card': card},
    }
    content = json.dumps(params, sort_keys=True)
    request = ImageSyncScanRequest.ImageSyncScanRequest()
    request.set_content(content.encode())
    resp = AliReqAction(request).do_req_action()
    data_info = {row['dataId']: row for row in resp['data']}[data_id]
    code, msg = data_info['code'], data_info['msg']
    if not (code == 200 and msg == 'OK'):
        logger.info(f'ocr_query__fail {data_id} {card} {code} {msg} resp: \n{resp}')
        return f'ocr_fail {code} {msg}'
    results = {row['scene']: row for row in data_info['results']}
    return results


def ocr_query(oss_url, data_id, ocr_type):
    """ OCR 查询 """
    if ocr_type not in ocr_type_cards_dic:
        return f'ocr_type_illegali {ocr_type}'
    card, info_key = ocr_type_cards_dic[ocr_type]
    resp = None
    try:
        results = ocr_req(oss_url, data_id, card)
        if not isinstance(results, dict):
            return '识别认证失败'
        data = results['ocr']
        assert isinstance(data, dict)
        suggestion = data['suggestion']
        result = data[info_key]
        assert isinstance(result, dict)
        result.update(
            _rate=data['rate'],
            _label=data['label'],
            _scene=data['scene'],
            _suggestion=suggestion,
        )
    except Exception as exc:
        exc_type = type(exc).__name__
        logger.info(f'ocr_query__error {data_id} {card} {exc_type} resp: \n{resp}')
        capture_exception(exc)
        logger.exception(exc)
        return f'ocr_error {exc_type}'
    return result


def ocr_query_scan(oss_url, data_id):
    """ 拍一拍 OCR 查询，二维码及车牌号 """
    ocr_type = mc.OCRType.VehicleNum.value
    card, info_key = ocr_type_cards_dic[ocr_type]
    result_qr, result_ocr = [], {}
    scenes = ['qrcode', 'ocr']
    resp = None
    try:
        results = ocr_req(oss_url, data_id, card, scenes=scenes)
        if not isinstance(results, dict):
            return '无法识别'
        data_ocr = results['ocr']
        data_qr = results['qrcode']
        assert isinstance(data_qr, dict)
        assert isinstance(data_ocr, dict)
        result_ocr = data_ocr.get(info_key, {})
        result_qr = data_qr.get('qrcodeData', [])
    except Exception as exc:
        exc_type = type(exc).__name__
        logger.info(f'ocr_query__error {data_id} {card} {exc_type} resp: \n{resp}')
        capture_exception(exc)
        logger.exception(exc)
    return result_qr, result_ocr
