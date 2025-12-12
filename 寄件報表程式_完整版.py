# Source Generated with Decompyle++
# File: 寄件報表程式.pyc (Python 3.11)
# 已手動修正縮排和不完整的部分

import os
import requests
from datetime import datetime

ToolVersion = '0.08'
title = '米匯寶-寄件報表程式  Ver ' + ToolVersion
remark = '主要更新：add boncpu.cc'
api_data_list = [
    'trading168.cc',
    'water1688.cc',
    'jy3331.com',
    'water168.shop',
    'procpu.cc',
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
    for a in range(len(api_data_list)):
        print(str(a) + str('.取得資料: ') + str(api_data_list[a]))
    print('0.结 束 程 式')
    print('-')


def select_date(select_mall):
    e5_date = input('請輸入您欲匯出的日期(今天不輸入,前一天1,前兩天2):')
    print('選擇的商城:', select_mall, ' 選擇的日期:', e5_date)
    get_ship(select_mall, e5_date)


def get_ship(select_mall, e5_date):
    try:
        r = requests.get('https://apiinternal.' + api_data_list[select_mall] + '/get_ship_info', params={
            'e5_passwd': '2d6um@fZ.?=Q8qF7SS6seaW?QP3d!?!T',
            'e5_date': e5_date})
        with open('米匯寶-寄件資料-' + api_data_list[select_mall] + '.xls', mode='wb') as f:
            f.write(r.content)
    except Exception as e:
        print('错误!', '米匯寶-报表汇出程式-寄件資料连线失败!', e)
    input('匯出完畢,請按任意鍵返回主選單')


# 主程式
while True:
    menu()
    choice = int(input('请输入您的选择:'))
    print('已選擇: ', choice)
    select_date(choice)
