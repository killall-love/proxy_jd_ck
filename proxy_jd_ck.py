#!/usr/bin/env python
# -*- coding: utf-8 -*

import time
import json
import requests
import websocket
from datetime import datetime

# 时间戳


def get_time():
    return int(round(time.time() * 1000))

# 钉钉失败消息推送


def send_error_message(error):
    if d_d_token == '':
        print("d_d_token未配置")
        return
    msg_body = {
        "msgtype": "text",
        "text": {
            "content": error
        },
        "at": {
            "isAtAll": False
        }
    }
    requests.post(
        url='https://oapi.dingtalk.com/robot/send?access_token={0}'.format(
            d_d_token),
        headers={'content-type': 'application/json;charset=utf-8'},
        data=json.dumps(msg_body)
    )

# 钉钉成功消息推送


def send_success_message(status, remarks):
    if d_d_token == '' or d_d_img == '':
        print("d_d_token or d_d_img is null")
        return
    msg_body = {
        "msgtype": "actionCard",
        "actionCard": {
            "title": "某东{0}消息推送".format(status),
            "text": "![screenshot]({0}) \n\n #### 某东{1}消息推送 \n\n\n\n 用户账号：{2} \n\n 操作时间：{3} \n\n操作类型：{4}Cookie成功".format(
                d_d_img,
                status,
                remarks, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                status)
        }
    }
    requests.post(
        url='https://oapi.dingtalk.com/robot/send?access_token={0}'.format(
            d_d_token),
        headers={'content-type': 'application/json;charset=utf-8'},
        data=json.dumps(msg_body)
    )

# 用户是否存在


def get_user_nums():
    rq = requests.get(
        url='{0}/api/envs?searchValue=&t={1}'.format(ql_url, get_time()), headers=get_ql_token())
    jp = json.loads(rq.text)
    if jp['code'] == 200:
        return len(jp['data'])
    return 0
# 用户是否存在


def is_user(pt_pin):
    rq = requests.get(url='{0}/api/envs?searchValue=pt_pin={1};&t={2}'.format(
        ql_url, pt_pin, get_time()), headers=get_ql_token())
    jp = json.loads(rq.text)
    if jp['code'] == 200:
        if len(jp['data']) != 0:
            return [jp['data'][0]['_id'], jp['data'][0]['remarks']]
    return []

# 更新


def ql_ck_update(user, pt_pin, pt_key):
    cookie = 'pt_pin={0}; pt_key={1};'.format(pt_pin, pt_key)
    rq = requests.put(url='{0}/api/envs?t={1}'.format(ql_url, get_time()),
                      headers=get_ql_token(), data=json.dumps({
                          "_id": user[0],
                          "value": cookie,
                          "name": "JD_COOKIE",
                          "remarks": user[1]
                      }))
    jp = json.loads(rq.text)
    if(jp['code'] == 200):
        remarks = jp['data']['remarks']
        print("update success 用户：{0} 时间：{1}".format(
            remarks, jp['data']['timestamp']))
        rq = requests.put(url='{0}/api/envs/enable?t={1}'.format(ql_url, get_time()),
                          headers=get_ql_token(), data=json.dumps([user[0]]))
        jp = json.loads(rq.text)
        if(jp['code'] == 200):
            print("启用成功")
            send_success_message("更新", remarks)

# 保存


def ql_ck_save(pt_pin, pt_key):
    cookie = 'pt_pin={0}; pt_key={1};'.format(pt_pin, pt_key)
    rq = requests.post(url='{0}/api/envs?t={1}'.format(ql_url, get_time()),
                       headers=get_ql_token(), data=json.dumps([{
                           "value": cookie,
                           "name": "JD_COOKIE",
                           "remarks": pt_pin
                       }]))
    jp = json.loads(rq.text)
    if(jp['code'] == 200):
        remarks = jp['data'][0]['remarks']
        print("save success 用户：{0} 时间：{1}".format(
            remarks, jp['data'][0]['timestamp']))
        send_success_message("添加", remarks)

# 获取qltoken


def get_ql_token():
    jp = read_ql_conf('{}/config/auth.json'.format(ql_path))
    token = jp['token']
    headers = {
        'Content-Type': 'application/json',
        "Authorization": "Bearer {}".format(token)
    }
    return headers

# 保存或者更新 Cookie


def saveOrUpdate(pt_pin, pt_key):
    user = is_user(pt_pin)
    if len(user) == 0:
        ql_ck_save(pt_pin, pt_key)
    else:
        ql_ck_update(user, pt_pin, pt_key)

# 格式化Cookie


def format_cookie(cookies):
    lists = cookies.split(';')
    cookie = {}
    for i in lists:
        j = i.strip()
        j = j.split('=')
        cookie[j[0]] = j[1]
    return cookie

# websocket监听


def get_cookie_key(ws, message):
    try:
        jp = json.loads(message)
        if len(jp['content']) == 0:
            send_error_message("操作失败，请挂代理或者安装证书后重试！！")
            print("请挂代理或者安装证书后重试！")
            return
        content = jp['content'][0]
        if 'https://un.m.jd.com/cgi-bin/app/appjmp?tokenKey=' in content['url']:
            if bool(1-ql_allow_add):
                send_error_message("添加失败，禁止添加！")
                print("禁止添加")
                return
            if get_user_nums() > ql_max_cookie:
                send_error_message("添加失败，人数满了！")
                print("添加人数满了")
                return
            cks = format_cookie(content['reqHeader']['Cookie'])
            saveOrUpdate(cks['pt_pin'], cks['pt_key'])
    except Exception as e:
        print(e)
        send_error_message("卧槽！失败了?????\n\n请联系管理员!\n\n错误详情："+str(e))
    finally:
        pass

# 读取ql配置文件


def read_ql_conf(path):
    with open(path, encoding='utf-8') as f:
        line = f.read()
        return json.loads(line)

# 初始化连接


def init():
    ws = websocket.WebSocketApp(
        "ws://127.0.0.1:8002/do-not-proxy", on_message=get_cookie_key)
    ws.run_forever(ping_timeout=30)


# ql目录
ql_path = '/ql'
# ql地址
ql_url = 'http://127.0.0.1:5700'
# 是否允许添加和更新
ql_allow_add = True
# 限制人数
ql_max_cookie = 42
# 钉钉推送Token
d_d_token = ''
# 钉钉推送背景
d_d_img = 'https://img11.360buyimg.com/ddimg/jfs/t1/204518/12/4557/1042310/61323f2aE622c0beb/7780a7f5c385f07d.jpg'


if __name__ == "__main__":
    print("""
    ////////////////////////////////////////////////////////////////////
//                          _ooOoo_                               //
//                         o8888888o                              //
//                         88" . "88                              //
//                         (| ^_^ |)                              //
//                         O\  =  /O                              //
//                      ____/`---'\____                           //
//                    .'  \\|     |//  `.                         //
//                   /  \\|||  :  |||//  \                        //
//                  /  _||||| -:- |||||-  \                       //
//                  |   | \\\  -  /// |   |                       //
//                  | \_|  ''\---/''  |   |                       //
//                  \  .-\__  `-`  ___/-. /                       //
//                ___`. .'  /--.--\  `. . ___                     //
//              ."" '<  `.___\_<|>_/___.'  >'"".                  //
//            | | :  `- \`.;`\ _ /`;.`/ - ` : | |                 //
//            \  \ `-.   \_ __\ /__ _/   .-` /  /                 //
//      ========`-.____`-.___\_____/___.-`____.-'========         //
//                           `=---='                              //
//      ^^^^^^^^^^^^^^^^^^^^^^^JD^^^^^^^^^^^^^^^^^^^^^^^^^        //
//            佛祖保佑       永不宕机     永无BUG                  //
////////////////////////////////////////////////////////////////////
    """)
    init()
