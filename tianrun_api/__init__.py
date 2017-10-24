import hashlib
import json
import time
import urllib.parse

import requests


class TianRunApi:

    DEFAULT_TIMEOUT = 20

    class TimeoutException(Exception):
        msg = '连接天润网关超时'

    class CallException(Exception):
        """
        code:
        """
        code_mapping = {
            '1': '呼叫座席失败',
            '2': '参数不正确',
            '3': '用户验证没有通过',
            '4': '账号被停用',
            '5': '资费不足',
            '6': '指定的业务尚未开通',
            '7': '电话号码不正确',
            '8': '座席工号（cno）不存在',
            '9': '座席状态不为空闲，可能未登录或忙',
            '10': '其他错误',
            '11': '电话号码为黑名单',
            '12': '座席不在线',
            '13': '座席正在通话/呼叫中',
            '14': '外显号码不正确',
            '33': '在外呼中或者座席振铃、通话中等',
            '40': '外呼失败，外呼号码次数超过限制',
            '41': '企业状态错误',
        }

        def __init__(self, code):
            self.code = code

        def __str__(self):
            return 'CallException, code: {}, msg: {}'.format(
                self.code, self.msg())

        @property
        def msg(self):
            return self.code_mapping.get(self.code)

    class HangupException(Exception):

        def __init__(self, msg):
            self.msg = msg

    class ClientException(Exception):

        def __init__(self, code, msg):
            self.code = code
            self.msg = msg

    class CdrException(Exception):

        def __init__(self, msg):
            self.msg = msg

    HOST = 'http://api.clink.cn'

    def __init__(self, enterprise_id, user_name, password, timeout=None):
        """
        :param enterprise_id: 管理员后台登陆后，位于右上角位置
        :param user_name: 登录后台用户名，如admin
        :param password: 上述用户的密码
        :param timeout: 最长等待时间
        """
        self.enterprise_id = enterprise_id
        self.user_name = user_name
        self.password = password
        self.session = requests.session()
        if not timeout:
            self.timeout = self.DEFAULT_TIMEOUT
        else:
            self.timeout = timeout

    @staticmethod
    def _encrypt_passwd(passwd, seed=None):
        result = hashlib.md5(passwd.encode()).hexdigest()
        if not seed:
            return result
        else:
            return hashlib.md5((result + seed).encode()).hexdigest()

    def call(self, cno, passwd, customer_number, ext_info=None):
        """
        :param cno: 客席号
        :param passwd: 登录密码
        :param customer_number: 客户电话号码
        :param ext_info: dict 或 字符 或数字，存在电话记录的用户自定义里面，
                         用来对应我们的记录和天润的记录之间的关系
        :return:
        """
        url = urllib.parse.urljoin(self.HOST, '/interface/PreviewOutcall')
        data = {
            'enterpriseId': self.enterprise_id,
            'cno': cno,
            'pwd': self._encrypt_passwd(passwd),
            'customerNumber': customer_number,
            'sync': '1',
        }
        if ext_info:
            if isinstance(ext_info, dict):
                json_str = json.dumps(ext_info)
                json_str = json_str.replace('"', r'\"')
                data['userField'] = json_str
            elif isinstance(ext_info, (int, str)):
                data['userField'] = str(ext_info)
        try:
            resp = self.session.post(url, data=data, timeout=self.timeout)
        except requests.Timeout:
            raise self.TimeoutException()
        # resp = self.session.get(url, params=data)
        result = json.loads(resp.text)
        res_no = result.get('res')
        if res_no != '0':
            raise self.CallException(res_no)

        return {
            'unique_id': result.get('uniqueId')
        }

    def hangup(self, unique_id):
        """
        :param unique_id:
        :return:
            success without return value, error with Exception
        """
        url = urllib.parse.urljoin(self.HOST,
                                   '/interface/entrance/OpenInterfaceEntrance')
        seed = str(int(time.time() * 1000))
        data = {
            'interfaceType': 'hangup',
            'enterpriseId': self.enterprise_id,
            'userName': self.user_name,
            'pwd': self._encrypt_passwd(self.password, seed),
            'seed': seed,
            'uniqueId': unique_id,
        }
        try:
            resp = self.session.post(url, data=data, timeout=self.timeout)
        except requests.Timeout:
            raise self.TimeoutException()
        result = json.loads(resp.text)
        res_no = result.get('result')
        if res_no != '1':
            raise self.HangupException(result.get('description'))
        return result

    def bind(self, cno, phone_no):
        """
        :param cno: 客席号
        :param phone_no: 绑定的电话号码
        :return:
            success without return, error with ClientException
        """
        url = urllib.parse.urljoin(self.HOST, '/interface/client/ClientOnline')
        seed = str(int(time.time() * 1000))
        data = {
            'enterpriseId': self.enterprise_id,
            'userName': self.user_name,
            'pwd': self._encrypt_passwd(self.password, seed),
            'seed': seed,
            'cno': cno,
            'status': '1',
            'bindTel': phone_no,
            'type': '1',
        }
        try:
            resp = self.session.post(url, data=data, timeout=self.timeout)
        except requests.Timeout:
            raise self.TimeoutException()
        result = json.loads(resp.text)
        res_no = result.get('code')
        if res_no != '0':
            raise self.ClientException(res_no, result.get('msg'))

    def unbind(self, cno):
        """
        :param cno: 客席号
        :return:
            success without return, error with ClientException
        """
        url = urllib.parse.urljoin(self.HOST, '/interface/client/ClientOffline')
        seed = str(int(time.time() * 1000))
        data = {
            'enterpriseId': self.enterprise_id,
            'userName': self.user_name,
            'pwd': self._encrypt_passwd(self.password, seed),
            'seed': seed,
            'cno': cno,
            'unBind': '1',
        }
        try:
            resp = self.session.post(url, data=data, timeout=self.timeout)
        except requests.Timeout:
            raise self.TimeoutException()
        result = json.loads(resp.text)
        res_no = result.get('code')
        if res_no != '0':
            raise self.ClientException(res_no, result.get('msg'))

    def cdr_detail(self, unique_id):
        """
        :param unique_id: unique_id
        :return:
            status	接听状态
            start_time	座席接听时间
            answer_time	客户接听时间
            end_time	结束时间
            bill_duration   计费时长
            cost	费用（元）
            sip_cause	呼叫结果
        """
        url = urllib.parse.urljoin(
            self.HOST, '/interfaceAction/cdrObInterface!listCdrObDetail.action')
        seed = str(int(time.time() * 1000))
        data = {
            'enterpriseId': self.enterprise_id,
            'userName': self.user_name,
            'pwd': self._encrypt_passwd(self.password, seed),
            'seed': seed,
            'id': unique_id,
        }
        try:
            resp = self.session.post(url, data=data, timeout=self.timeout)
        except requests.Timeout:
            raise self.TimeoutException()
        result = json.loads(resp.text)
        res_no = result.get('result')
        if res_no != 'success':
            raise self.CdrException(result.get('msg'))

        records = result.get('msg')
        if records:
            data = result.get('msg')[0]
        else:
            raise self.CdrException('记录不存在')

        return {
            'status': data['status'],
            'start_time': data['startTime'],
            'answer_time': data['answerTime'],
            'end_time': data['endTime'],
            'bill_duration': data['billDuration'],
            'cost': data['cost'],
            'combo_cost': data['comboCost'],
            'sip_cause': data['sipCause'],
        }

    def cdr_info(self, unique_id):
        """
        :param unique_id: unique_id
        :return:

            status: 外呼结果
            start_time: 电话进入系统时间
            bridge_time: 客户接听时间
            bridge_duration: 通话时长
            cost: 费用(元)
            total_duration: 总时长
            record_file: 录音文件的最终地址及录音文件名
            user_field: 用户自定义参数
            sip_cause: 呼叫结果
        :refer:
         http://docs.ti-net.com.cn/index.php?m=content&c=index&a=lists&catid=34
        """
        url = urllib.parse.urljoin(
            self.HOST, '/interfaceAction/cdrObInterface!listCdrOb.action')
        seed = str(int(time.time() * 1000))
        data = {
            'enterpriseId': self.enterprise_id,
            'userName': self.user_name,
            'pwd': self._encrypt_passwd(self.password, seed),
            'seed': seed,
            'uniqueId': unique_id,
        }
        try:
            resp = self.session.post(url, data=data, timeout=self.timeout)
        except requests.Timeout:
            raise self.TimeoutException()
        result = json.loads(resp.text)
        res_no = result.get('result')
        if res_no != 'success':
            raise self.CdrException(result.get('msg'))
        records = result.get('msg').get('data')
        if records:
            data = records[0]
        else:
            raise self.CdrException('记录不存在')
        return {
            'status': data['status'],
            'start_time': data['startTime'],
            # 'end_time': data['endTime'],
            'bridge_time': data['bridgeTime'],
            'bridge_duration': data['bridgeDuration'],
            'cost': data['cost'],
            'total_duration': data['totalDuration'],
            'record_file': data['recordFile'],
            'user_field': data['userField'],
            'sip_cause': data['sipCause'],
        }

    def cdr_infos(self, start_time=None, end_time=None):
        url = urllib.parse.urljoin(
            self.HOST, '/interfaceAction/cdrObInterface!listCdrOb.action')
        seed = str(int(time.time() * 1000))
        data = {
            'enterpriseId': self.enterprise_id,
            'userName': self.user_name,
            'pwd': self._encrypt_passwd(self.password, seed),
            'seed': seed,
            'limit': 1000,
        }
        if start_time:
            data['startTime'] = start_time
        if end_time:
            data['endTime'] = end_time
        try:
            resp = self.session.post(url, data=data, timeout=self.timeout)
        except requests.Timeout:
            raise self.TimeoutException()
        result = json.loads(resp.text)
        res_no = result.get('result')
        if res_no != 'success':
            raise self.CdrException(result.get('msg'))
        records = result.get('msg').get('data')
        results = []
        for data in records:
            tmp_record = {
                'status': data['status'],
                'start_time': data['startTime'],
                # 'end_time': data['endTime'],
                'bridge_time': data['bridgeTime'],
                'bridge_duration': data['bridgeDuration'],
                'cost': data['cost'],
                'total_duration': data['totalDuration'],
                'record_file': data['recordFile'],
                'user_field': data['userField'],
                'sip_cause': data['sipCause'],
            }
            results.append(tmp_record)
        return results
