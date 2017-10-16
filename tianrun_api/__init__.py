import hashlib
import json
import time
import urllib.parse

import requests


class TianRunApi:

    class TimeoutException(Exception):
        pass

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

        def msg(self):
            return self.code_mapping.get(self.code)

    class ClientException(Exception):

        def __init__(self, code, msg):
            self.code = code
            self.msg = msg

    HOST = 'http://api.clink.cn'

    def __init__(self, enterprise_id, user_name, password):
        """
        :param enterprise_id: 管理员后台登陆后，位于右上角位置
        :param user_name: 登录后台用户名，如admin
        :param password: 上述用户的密码
        """
        self.enterprise_id = enterprise_id
        self.user_name = user_name
        self.password = password
        self.session = requests.session()

    @staticmethod
    def _encrypt_passwd(passwd, seed=None):
        result = hashlib.md5(passwd.encode()).hexdigest()
        if not seed:
            return result
        else:
            return hashlib.md5((result + seed).encode()).hexdigest()

    def call(self, cno, passwd, customer_number):
        """
        :param cno: 客席号
        :param passwd: 登录密码
        :param customer_number: 客户电话号码
        :return:
        """
        url = urllib.parse.urljoin(self.HOST, '/interface/PreviewOutcall')
        data = {
            'enterpriseId': self.enterprise_id,
            'cno': cno,
            'pwd': self._encrypt_passwd(passwd),
            'customerNumber': customer_number,
            'userField': '123',
            'sync': '1',
        }
        resp = self.session.post(url, data=data)
        result = json.loads(resp.text)
        res_no = result.get('res')
        if res_no != '0':
            raise self.CallException(res_no)

        return result

    def bind(self, cno, phone_no):
        """
        :param cno: 客席号
        :param phone_no: 绑定的电话号码
        :return:
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
        resp = self.session.post(url, data=data)
        result = json.loads(resp.text)
        res_no = result.get('code')
        if res_no != '0':
            raise self.ClientException(res_no, result.get('msg'))

        return result

    def unbind(self, cno):
        """
        :param cno: 客席号
        :return:
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
        resp = self.session.post(url, data=data)
        result = json.loads(resp.text)
        res_no = result.get('code')
        if res_no != '0':
            raise self.ClientException(res_no, result.get('msg'))

        return result
