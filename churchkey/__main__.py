#!/usr/bin/python

'''
churchkey: A program tunneling SSH through HTTP proxies with authentication.

Copyright (C) 2016 Cyker Way

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import argparse
import base64
import hashlib
import http.client
import os
import random
import select
import socket
import sys
import traceback

# Program version.
VERSION = '1.0.0'

# Buffer size for read and write.
BUFSIZE = 4096

# Global config.
config = {}

def md5(str_):
    '''
    Return MD5 checksum of the given string.

    Parameters
    ----------
    plaintext
        Input string.

    Returns
    -------
    str_ : str
        MD5 checksum in hex format.
    '''
    return hashlib.md5(str_.encode()).hexdigest()

def parse_args():
    '''
    Parse command-line arguments.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'proxy_host', type=str, default='127.0.0,1', help='proxy host')
    parser.add_argument(
        'proxy_port', type=int, default=3128, help='proxy port')
    parser.add_argument(
        'dest_host', type=str, default='127.0.0.1', help='dest host')
    parser.add_argument(
        'dest_port', type=int, default=22, help='dest port')
    parser.add_argument(
        'auth_file', type=str, default=os.path.expanduser('~/.ssh/proxyauth'),
        help='auth file')
    parser.add_argument(
        '--verbose', action='store_true', help='display verbose output')
    parser.add_argument(
        '--version', action='version', version='%(prog)s {}'.format(VERSION),
        help='show version')

    args = parser.parse_args()

    config['parser'] = parser
    config['proxy_host'] = args.proxy_host
    config['proxy_port'] = args.proxy_port
    config['dest_host'] = args.dest_host
    config['dest_port'] = args.dest_port
    if os.path.isfile(args.auth_file):
        with open(args.auth_file, 'rt') as f:
            username, password = f.readline().strip().split(':')
        config['username'] = username
        config['password'] = password
    elif os.path.exists(args.auth_file):
        raise Exception('{} is not a regular file'.format(args.auth_file))
    config['verbose'] = args.verbose

def probe():
    '''
    Probe the proxy to see whether authentication is needed.

    Returns
    -------
    HTTPResponse
        An HTTP response object.
    '''
    conn = http.client.HTTPConnection(config['proxy_host'],
                                      config['proxy_port'])
    conn.request('CONNECT',
                 config['dest_host'] + ':' + str(config['dest_port']))
    resp = conn.getresponse()
    conn.close()
    return resp

def parse_auth_header(auth_header):
    '''
    Parse authentication header in proxy response.

    Parameters
    ----------
    auth_header
        The header to parse.

    Returns
    -------
    scheme : str
        The auth scheme (basic or digest).
    fields : dict
        A dict of header fields.
    '''
    scheme, fields_str = auth_header.split(' ', 1)
    scheme = scheme.lower()
    fields = {}
    for item in fields_str.split(', '):
        key, value = item.split('=')
        key = key.lower()
        if key in ['realm', 'nonce', 'qop']:
            value = value[1:-1].replace('\"', '"')  # unquote
        elif key in ['stale']:
            value = value.lower() == 'true'
        fields[key] = value
    return scheme, fields

def basic_auth():
    '''
    Basic access authentication.

    Returns
    -------
    str
        Authorization header.
    '''
    username = config['username']
    password = config['password']
    result = base64.b64encode((username + ':' + password).encode()).decode()
    return 'Basic ' + result

def digest_auth(fields):
    '''
    Digest access authentication.

    Parameters
    ----------
    fields
        Authentication header fields.

    Returns
    -------
    str
        Authorization header.
    '''
    username = config['username']
    realm = fields['realm']
    password = config['password']
    HA1 = md5('{}:{}:{}'.format(username, realm, password))
    nonce = fields['nonce']
    nc = '00000001'
    cnonce = hex(random.randint(0, 0xffffffff))[2:]
    qop = fields['qop']
    dest_host = config['dest_host']
    dest_port = config['dest_port']
    HA2 = md5('{}:{}:{}'.format('CONNECT', dest_host, str(dest_port)))
    response = md5(':'.join((HA1, nonce, nc, cnonce, qop, HA2)))

    return (
        'Digest ' 'username="{username}", ' 'realm="{realm}", '
        'nonce="{nonce}", ' 'uri="{dest_host}:{dest_port}", ' 'qop={qop}, '
        'nc={nc}, ' 'cnonce="{cnonce}", ' 'response="{response}"'
    ).format(
        username=username, realm=realm, nonce=nonce, dest_host=dest_host,
        dest_port=dest_port, qop=qop, nc=nc, cnonce=cnonce, response=response)

def build_request_head(auth_header):
    '''
    Build request head using authorization header.

    Parameters
    ----------
    auth_header
        Authorization header.

    Returns
    -------
    bytes
        Request head.
    '''
    uri = '{}:{}'.format(config['dest_host'], config['dest_port'])
    head = ('CONNECT {uri} HTTP/1.0\n' 'Host: {uri}\n').format(uri=uri)
    if auth_header is not None:
        head += (
            'Proxy-Authorization: {auth_header}\n'
            '\n'
        ).format(auth_header=auth_header)
    head = head.encode()
    return head

def send_request(head):
    '''
    Send CONNECT request to proxy and start forwarding data.

    Parameters
    ----------
    head
        Request head.
    '''
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((config['proxy_host'], config['proxy_port']))
        sock.sendall(head)

        while True:
            ready, _, _ = select.select([sock, sys.stdin], [], [])
            if sock in ready:
                data = sock.recv(BUFSIZE)
                if len(data) == 0:
                    break
                os.write(sys.stdout.fileno(), data)
            if sys.stdin in ready:
                data = os.read(sys.stdin.fileno(), BUFSIZE)
                if len(data) == 0:
                    break
                sock.sendall(data)

def run():
    '''
    Run this script.
    '''
    # Parse arguments.
    parse_args()
    verbose = config['verbose']
    if verbose:
        print(config)

    # Initial probe.
    resp = probe()
    if verbose:
        print(resp.getheaders())

    # See if auth is needed.
    if resp.status == 407:
        auth_header = resp.getheader('Proxy-Authenticate')
        scheme, fields = parse_auth_header(auth_header)
        if scheme == 'basic':
            auth_header = basic_auth()
        elif scheme == 'digest':
            auth_header = digest_auth(fields)
        else:
            raise Exception('unknown auth scheme')
    elif resp.status // 100 * 100 == 200:
        auth_header = None
    else:
        raise Exception('Error: {} {}'.format(resp.status, resp.reason))

    # Make request head.
    head = build_request_head(auth_header)
    if verbose:
        print(head)

    # Send the request.
    send_request(head)

def usage():
    '''
    Display usage text.
    '''
    config['parser'].print_help()

def main():
    '''
    Main function.
    '''
    try:
        run()
    except Exception:
        traceback.print_exc()
        usage()
        sys.exit(1)

if __name__ == '__main__':
    main()

