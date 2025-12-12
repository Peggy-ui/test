# Source Generated with Decompyle++
# File: 資料匯入程式.pyc (Python 3.11)
# 已手動修正縮排和不完整的部分

import os
import requests
import json
from datetime import datetime

ToolVersion = '0.24'
title = '米匯寶-資料匯入程式  Ver ' + ToolVersion
remark = '主要更新：add boncpu.cc'
host_api_list = [
    'trading168.cc',
    'water1688.cc',
    'jy3331.com',
    'water168.shop',
    'procpu.cc',
    'water888.cc',
    'chipcpu.cc',
    'elecpu.cc',
    'vegacpu.shop',
    'shellcpu.shop',
    'telancpu.shop',
    'vatcpu.cc',
    'katcpu.cc',
    'tectcpu.cc',
    'camcpu.cc',
    'boncpu.cc']


def menu():
    os.system('cls')
    print(title)
    print(remark)
    print('-')
    aaa = 1
    for a in range(len(host_api_list)):
        print(str(aaa) + str('.匯入地址: ') + str(host_api_list[a]))
        aaa += 1
    print('==============================')
    for a in range(len(host_api_list)):
        print(str(aaa) + str('.匯入訂單: ') + str(host_api_list[a]))
        aaa += 1
    print('==============================')
    for a in range(len(host_api_list)):
        print(str(aaa) + str('.匯入採購單: ') + str(host_api_list[a]))
        aaa += 1
    print('0.結 束 程 式')
    print('-')


def up_to_mall(select_mall):
    # 匯入地址 (選項 1 ~ 16)
    if int(select_mall) <= len(host_api_list):
        try:
            print('選擇的商城', host_api_list[int(select_mall) - 1])
            url = 'https://apiinternal.' + str(host_api_list[select_mall - 1]) + '/query_pending_orders'
            postbody = {
                'd1_password': '9=Hev%wZmtR9fFaGXxWq+cWdf+h$GWQk'}
            check_d1 = requests.request('POST', url, data=json.dumps(postbody).encode('utf-8'), timeout=600)
            print(check_d1.text)
            print(check_d1.status_code)

            # 驗證剩餘單數
            if str(json.loads(check_d1.text)['data']) != '0':
                print('錯誤!', '米匯寶-匯入地址資料程式-剩餘單數不為0!剩餘單數:', check_d1.text)
                input('請確認錯誤(匯入地址)')
                return

            # 匯入地址
            url = 'https://apiinternal.' + str(host_api_list[select_mall - 1]) + '/import_address?password=SbT?.%23mkMKp8D5qy6mk?vhzc9%23Y4uhFy'
            print('選擇的商城:', str(host_api_list[select_mall - 1]))
            print('資料處理中，請勿做其他動作。')
            files = [('file', ('1.txt', open('1.txt', 'rb'), 'text/plain'))]
            r = requests.post(url, files=files, timeout=600)

        except Exception as e:
            print('錯誤!', '米匯寶-匯入地址資料程式-失敗!', e)
            input('請確認錯誤(匯入地址)')
            return

    # 匯入訂單 (選項 17 ~ 32)
    elif int(select_mall) <= 2 * len(host_api_list):
        try:
            idx = select_mall - len(host_api_list) - 1
            url = 'https://apiinternal.' + str(host_api_list[idx]) + '/f7_import_order?password=SbT?.%23mkMKp8D5qy6mk?vhzc9%23Y4uhFy'
            print('選擇的商城:', str(host_api_list[idx]))
            print('資料處理中，請勿做其他動作。')
            files = [('file', ('2.txt', open('2.txt', 'rb'), 'text/plain'))]
            r = requests.post(url, files=files, timeout=600)
        except Exception as e:
            print('錯誤!', '米匯寶-匯入訂單資料程式-失敗!', e)
            input('請確認錯誤(匯入訂單)')
            return

    # 匯入採購單 (選項 33 ~ 48)
    elif int(select_mall) <= 3 * len(host_api_list):
        try:
            idx = select_mall - 2 * len(host_api_list) - 1
            url = 'https://apiinternal.' + str(host_api_list[idx]) + '/f7_import_purchase?password=SbT?.%23mkMKp8D5qy6mk?vhzc9%23Y4uhFy'
            print('選擇的商城:', str(host_api_list[idx]))
            print('資料處理中，請勿做其他動作。')
            files = [('file', ('3.txt', open('3.txt', 'rb'), 'text/plain'))]
            r = requests.post(url, files=files, timeout=600)
        except Exception as e:
            print('錯誤!', '米匯寶-匯入採購單資料程式-失敗!', e)
            input('請確認錯誤(匯入採購單)')
            return

    input('匯入完畢,請按任意鍵返回主選單')


# 主程式
while True:
    menu()
    print('匯入地址的檔案命名為1.txt')
    print('匯入訂單的檔案命名為2.txt')
    print('匯入採購單的檔案命名為3.txt')
    print('請將欲匯入的檔案並放入本程式同目錄下')
    select_mall = int(input('請輸入您的選擇:'))
    print('已選擇: ', select_mall)
    up_to_mall(select_mall)
