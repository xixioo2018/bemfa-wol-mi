# See PyCharm help at https://www.jetbrains.com/help/pycharm/
import re
import struct
import subprocess

import paho.mqtt.client as mqtt
import socket

import paramiko
from loguru import logger

HOST = 'bemfa.com'
PORT = 9501
token = ''  # 巴法云的私钥
cmd_off = 'curl -s "https://api.bemfa.com/api/device/v1/data/3/push/get/?uid=%s&topic=PCC001&msg=off" -w "\n"' % token
cmd_on = 'curl -s "https://api.bemfa.com/api/device/v1/data/3/push/get/?uid=%s&topic=PCC001&msg=on" -w "\n"' % token

default_mac_address = '00-D8-61-7B-62-EB'  # 本机的MAC地址
default_brd = '192.168.2.255'
default_ip = '192.168.2.134'  # 本机固定Ip
pc_user = 'xx'  # 本机登录用户名
pc_password = 'xxxxxx'  # 本机登录密码

cmd1 = 'timeout 0.1 ping -c 1 ' + default_ip


def get_pc_state():
    std_out = subprocess.run(cmd1, shell=True, stdout=subprocess.PIPE).stdout
    if len(std_out) == 0:
        return False
    else:
        return True


def shutdown_pc():
    global default_ip
    global pc_user
    global pc_password

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(default_ip, username=pc_user, password=pc_password)
    stdin, stdout, stderr = ssh_client.exec_command('shutdown -s -f -c "小爱将在5秒内关闭这个电脑" -t 5')

    if ssh_client is not None:
        ssh_client.close()
        del ssh_client, stdin, stdout, stderr


# Check MAC address
def check_mac(mac_addr):
    # Length check
    if len(mac_addr) == 12:
        pass
    elif len(mac_addr) == 17:
        mac_addr = mac_addr.replace(':', '')
    else:
        return False
    # Regex check
    pattern = re.compile(r'[0-9A-Fa-f]{12}')
    result = pattern.match(mac_addr)
    if result is not None:
        return True
    else:
        return False


# WOL function, Call on demand
def wake_on_lan(mac):
    logger.info("wake_on_lan: {0}".format(mac))
    if len(mac) == 12:
        pass
    elif len(mac) == 17:
        mac = mac.replace(':', '')
        mac = mac.replace('-', '')
    else:
        raise ValueError('Incorrect MAC address')

    if check_mac(mac):
        data = 'FFFFFFFFFFFF' + mac * 16
        byte_data = b''
        for i in range(0, len(data), 2):
            byte_dat = struct.pack('B', int(data[i: i + 2], 16))
            byte_data = byte_data + byte_dat
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        logger.info("wake_on_lan: {0}".format(default_brd))
        sock.sendto(byte_data, (default_brd, 9))  # If your IP is 192.168.0.x, change to 192.168.0.255
        sock.close()
        logger.info("wake_on_lan: 执行完成")
    else:
        raise ValueError('Incorrect MAC address')


# 连接并订阅
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("PCC001")  # 订阅消息


# 消息接收
def on_message(client, userdata, msg):
    print("主题:" + msg.topic + " 消息:" + str(msg.payload.decode('utf-8')))
    sw = str(msg.payload.decode('utf-8'))
    if sw == "on":
        wake_on_lan(default_mac_address)
        # os.system(cmd_on)
    else:
        shutdown_pc()
        # os.system(cmd_off)


# 订阅成功
def on_subscribe(client, userdata, mid, granted_qos):
    print("On Subscribed: qos = %d" % granted_qos)


# 失去连接
def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Unexpected disconnection %s" % rc)


if __name__ == '__main__':
    client = mqtt.Client(token)
    client.username_pw_set("userName", "passwd")
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_subscribe = on_subscribe
    client.on_disconnect = on_disconnect
    client.connect(HOST, PORT, 60)
    client.loop_forever()
