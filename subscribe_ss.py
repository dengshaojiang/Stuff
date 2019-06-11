# -*- coding: UTF-8 -*-
import base64
import requests
import json
import socket
import time
from datetime import datetime
import logging
from eventlet import greenthread
#from eventlet.green import socket
import eventlet
eventlet.monkey_patch(all=True)

DEFAULT_LOG_FILE = "subscribe_ss.log"
DEFAULT_LOG_LEVEL = logging.DEBUG
DEFAULT_LOG_FORMAT = "%(asctime)s.%(msecs)03d %(levelname)8s [%(funcName)s:L%(lineno)d] %(message)s"
DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG = logging.getLogger(__name__)

def subscribe_airport(url):
    LOG.debug("subscribe_airport url: %s" % url)
    resp = requests.get(url)
    raw_b64 = resp.content
    missing_padding = 4 - len(raw_b64) % 4
    if missing_padding:
        raw_b64 += b'='* missing_padding
    #print raw_b64
    raw_b64 = raw_b64.replace("ssd://", "")
    decode_b64 = base64.urlsafe_b64decode(raw_b64)
    #b = a.decode("unicode-escape")

    decode_dict = json.loads(decode_b64)
    #print json.dumps(decode_dict, indent=2).decode("unicode-escape")
    return decode_dict

def parse_server_dict(airport_servers):
    ss_servers = []
    for s in airport_servers["servers"]:
       server = {}
       #server["remarks"] = "%.4s %sx " % (airport_servers["airport"], s["ratio"])
       server["remarks"] = "%sx " % s["ratio"]
       LOG.info(server["remarks"])
       server["remarks"] += s["remarks"][:8]
       server["server"] = s["server"]
       server["server_port"] = airport_servers["port"]
       server["password"] = airport_servers["password"]
       server["method"] = airport_servers["encryption"]
       server["timeout"] = 5
       ss_servers.append(server)
       greenthread.sleep(0)
    return ss_servers

def get_delay_server_twice(server_dict):
    for i in range(2):
        delay_ms = get_delay_server(server_dict)
        #if delay_ms == "Failed":
        #    break
        greenthread.sleep(0)

def get_delay_server(server_dict):
    s = None
    server_dict["delay"] = "Failed"
    host = server_dict["server"]
    port = server_dict["server_port"]
    LOG.debug("get_delay_server %s:%s..." % (host, port))
    time.sleep(1)
    begin = time.time()
    try:
        with eventlet.Timeout(3):
            s = socket.create_connection((host, port))
            s.close()
        end = time.time()
    except (eventlet.timeout.Timeout, Exception) as e:
    #except Exception as e:
        #print e
        end = time.time()
        delay_ms = (end - begin)*1000
        LOG.debug("Failed connect %s:%s %.1f ms" % (host, port, delay_ms))
        #server_dict["remarks"] = "[Failed] %s" % server_dict["remarks"]
        return "Failed"
    finally:
        if s:
            s.close()
    delay_ms = (end - begin)*1000
    LOG.debug("server %s:%s cost %.0f ms" % (host, port, delay_ms))
    #server_dict["remarks"] = "[%.0fms]%s" % (delay_ms, server_dict["remarks"])
    server_dict["delay"] = int(delay_ms)
    return delay_ms
    
    
def merge_cfg(servers, file_name="gui-config.json"):
    with open(file_name, 'r') as f:
        cfg = json.load(f)
    #ss_servers = parse_server_dict(server_dict)
    sort_servers = sorted(servers, lambda x, y: cmp(x["delay"], y["delay"]))
    for s in sort_servers:
        s["remarks"] = "[%sms]%s" % (s["delay"], s["remarks"])
    cfg["configs"] = sort_servers
    #print json.dumps(sort_servers, indent=2).decode("unicode-escape")
    with open(file_name, 'w') as f:
        cfg = json.dump(cfg, f, indent=2)


def parse_delay_servers(servers):
    jobs = [greenthread.spawn(get_delay_server_twice, server_dict=s) for s in servers]
    #gevent.joinall(jobs)
    #try:
    results = [j.wait() for j in jobs]
    #except eventlet.timeout.Timeout as e:
    #    pass
    #print json.dumps(servers, indent=2).decode("unicode-escape")


def subscribe_all(urls):
    
    airport_servers = []
    
    jobs = [greenthread.spawn(subscribe_airport, url=url) for url in urls]
    for j in jobs:
        ss_servers = parse_server_dict(j.wait())
        airport_servers.extend(ss_servers)
        greenthread.sleep(0)
    #print json.dumps(airport_servers, indent=2).decode("unicode-escape")
    '''
    airport_servers = [
    {
      "server": "en-3hd5.eimii.xyz",
      "server_port": 19347,
      "password": "iCeUCy",
      "method": "aes-256-gcm",
      "plugin": "",
      "plugin_opts": "",
      "plugin_args": "",
      "remarks": "KD 1x 英国 2 - 推荐",
      "timeout": 5
    },
    {
      "server": "us-ve43.eimii.xyz",
      "server_port": 19347,
      "password": "iCeUCy",
      "method": "aes-256-gcm",
      "plugin": "",
      "plugin_opts": "",
      "plugin_args": "",
      "remarks": "KD 1x 美国 2 - ",
      "timeout": 5
    },
    {
      "server": "546",
      "server_port": 19347,
      "password": "iCeUCy",
      "method": "aes-256-gcm",
      "plugin": "",
      "plugin_opts": "",
      "plugin_args": "",
      "remarks": "KD 1x 546",
      "timeout": 5
    },
    {
      "server": "jp-v8we.eimii.xyz",
      "server_port": 19347,
      "password": "iCeUCy",
      "method": "aes-256-gcm",
      "plugin": "",
      "plugin_opts": "",
      "plugin_args": "",
      "remarks": "KD 1x 日本 1 - 推荐",
      "timeout": 5
    },]
    '''
    parse_delay_servers(airport_servers)
    merge_cfg(airport_servers)


def load_url(file_name="subscribe_ss.txt"):
    urls = []
    with open(file_name, 'r') as f:
        for url in f.readlines():
            if url.find("#") == -1:
                urls.append(url.strip())
    return urls
    
def setup_logging(logfile=DEFAULT_LOG_FILE, level=DEFAULT_LOG_LEVEL):
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT,
                                  DEFAULT_LOG_DATE_FORMAT)
    handler = logging.FileHandler(logfile)
    
    handler.setFormatter(formatter)
    logging.root.setLevel(level)
    logging.root.addHandler(handler)
    
    
    import sys
    streamlog = logging.StreamHandler(sys.stderr)
    streamlog.setFormatter(formatter)
    logging.root.addHandler(streamlog)

if __name__ == "__main__":
    '''
    urls = [
        "https://kdrrr.net/link/HWqY0LxxMzZ0Z0Tb?mu=3",
        "https://ppyun.ml/link/9gcbN9iBZ8fciKwW?mu=3",
        "https://b.xn--9kq677j3ki.app/link/GC0PI9VYF9qlecmc?mu=3",
    ]
    '''
    setup_logging()
    begin = time.time()
    urls = load_url()
    subscribe_all(urls)
    end = time.time()
    cost = (end - begin) * 1000
    LOG.info("Cost %.1f ms" % cost)
