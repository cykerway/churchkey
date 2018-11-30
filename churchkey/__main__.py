#!/usr/bin/env python3

'''
a tool tunneling ssh over http proxy;
'''

from os.path import expanduser
from os.path import isfile
import argparse
import base64
import hashlib
import http.client
import logging
import os
import random
import select
import socket
import sys
import traceback

##  global config;
class conf: pass

def md5(s):

    '''
    return md5 checksum of given string;

    ## params

    s:str
    :   input string;

    ## return

    :str
    :   md5 checksum in hex format;
    '''

    return hashlib.md5(s.encode()).hexdigest()

def parse_args():

    '''
    parse command line arguments;
    '''

    parser = argparse.ArgumentParser()

    parser.add_argument(
        'proxy_host',
        default='127.0.0,1',
        help='proxy host;',
    )

    parser.add_argument(
        'proxy_port',
        type=int,
        default=3128,
        help='proxy port;',
    )

    parser.add_argument(
        'dest_host',
        default='127.0.0.1',
        help='dest host;',
    )

    parser.add_argument(
        'dest_port',
        type=int,
        default=22,
        help='dest port;',
    )

    parser.add_argument(
        'auth_file',
        default=expanduser('~/.ssh/proxyauth'),
        help='auth file;',
    )

    parser.add_argument(
        '--buf-size',
        type=int,
        default=4096,
        help='data buffer size;',
    )

    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='enable debug mode;',
    )

    args = parser.parse_args()

    return args

def probe_proxy():

    '''
    probe the proxy to check if authentication is needed;

    ## return

    :HTTPResponse
    :   http response object;
    '''

    conn = http.client.HTTPConnection(conf.proxy_host, conf.proxy_port)
    conn.request('CONNECT', conf.dest_host + ':' + str(conf.dest_port))
    resp = conn.getresponse()
    conn.close()
    return resp

def parse_auth_header(auth):

    '''
    parse authentication header in proxy response;

    ## params

    auth:str
    :   authentication header;

    ## return

    scheme:str
    :   authentication scheme (basic or digest);

    fields:dict
    :   a dict of header fields;
    '''

    scheme, fields_str = auth.split(' ', 1)
    scheme = scheme.lower()
    fields = {}
    for item in fields_str.split(', '):
        key, value = item.split('=')
        key = key.lower()
        if key in ['realm', 'nonce', 'qop']:
            value = value[1:-1].replace('\"', '"')
        elif key in ['stale']:
            value = (value.lower() == 'true')
        fields[key] = value
    return scheme, fields

def basic_auth():

    '''
    basic access authentication;

    ## return

    :str
    :   authorization header;
    '''

    plain = conf.username + ':' + conf.password
    result = base64.b64encode(plain.encode()).decode()
    return 'Basic ' + result

def digest_auth(fields):

    '''
    digest access authentication;

    ## params

    fields:
    :   authentication header fields;

    ## return

    :str
    :   authorization header;
    '''

    realm = fields.get('realm')
    nonce = fields.get('nonce')
    qop = fields.get('qop')

    username = conf.username
    password = conf.password
    dest_host = conf.dest_host
    dest_port = conf.dest_port

    ha1 = md5(':'.join((username, realm, password)))
    ha2 = md5(':'.join(('CONNECT', dest_host, str(dest_port))))

    if qop == 'auth':
        nc = '00000001'
        cnonce = '{:x}'.format(random.randint(0, 0xffffffff))
        response = md5(':'.join((ha1, nonce, nc, cnonce, qop, ha2)))
    else:
        response = md5(':'.join((ha1, nonce, ha2)))

    return 'Digest ' + ', '.join((
        f'username="{username}"',
        f'realm="{realm}"',
        f'nonce="{nonce}"',
        f'qop="{qop}"',
        f'nc="{nc}"',
        f'cnonce="{cnonce}"',
        f'response="{response}"',
        f'uri="{dest_host}:{dest_port}"',
    ))

def build_connect_req(auth):

    '''
    build *connect* request;

    ## params

    auth:str
    :   authorization header;

    ## return

    :bytes
    :   *connect* request;
    '''

    uri = '{}:{}'.format(conf.dest_host, conf.dest_port)

    head = (
        'CONNECT {uri} HTTP/1.0\n'
        'Host: {uri}\n'
    ).format(uri=uri)

    if auth is not None:
        head += (
            'Proxy-Authorization: {auth}\n'
        ).format(auth=auth)

    return (head + '\n').encode()

def main_loop(req):

    '''
    send *connect* request to proxy and relay data;

    ## params

    req:bytes
    :   *connect* request;
    '''

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:

        ##  send *connect* request;
        sock.connect((conf.proxy_host, conf.proxy_port))
        sock.sendall(req)

        ##  relay data;
        while True:
            ready, _, _ = select.select([sock, sys.stdin], [], [])
            if sock in ready:
                data = sock.recv(conf.buf_size)
                if len(data) == 0: break
                os.write(sys.stdout.fileno(), data)
            if sys.stdin in ready:
                data = os.read(sys.stdin.fileno(), conf.buf_size)
                if len(data) == 0: break
                sock.sendall(data)

def main():

    '''
    main function;
    '''

    ##  parse args;
    args = parse_args()

    ##  config logging;
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    ##  update config;
    conf.proxy_host = args.proxy_host
    conf.proxy_port = args.proxy_port
    conf.dest_host  = args.dest_host
    conf.dest_port  = args.dest_port
    conf.auth_file  = args.auth_file
    conf.buf_size   = args.buf_size

    ##  read auth file;
    if isfile(args.auth_file):
        with open(args.auth_file, 'rt') as f:
            conf.username, conf.password = f.readline().strip().split(':')

    for k, v in conf.__dict__.items():
        logging.debug('{}={}'.format(k, v))

    ##  probe proxy to check if auth is needed;
    resp = probe_proxy()
    logging.debug(resp.getheaders())
    if resp.status == 407:
        auth = resp.getheader('Proxy-Authenticate')
        scheme, fields = parse_auth_header(auth)
        if scheme == 'basic':
            auth = basic_auth()
        elif scheme == 'digest':
            auth = digest_auth(fields)
        else:
            raise Exception('unknown auth scheme: {};'.format(scheme))
    elif resp.status // 100 * 100 == 200:
        auth = None
    else:
        raise Exception(
            'connection error: {} {}'.format(resp.status, resp.reason))

    ##  build *connect* request;
    req = build_connect_req(auth)
    logging.debug(req)

    ##  send request and enter main loop;
    main_loop(req)

if __name__ == '__main__':
    main()

