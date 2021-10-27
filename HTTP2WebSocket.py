#!/usr/bin/python3
"""
    Author: Dawid Czarnecki
"""

import argparse
import time
import ssl

from datetime import datetime, timedelta
from time import sleep
from websocket import create_connection, _exceptions

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote

class proxyServer(BaseHTTPRequestHandler):
    post_body = ''

    def do_POST(self):
        self.path = '/'+self.path if self.path[0] != '/' else self.path # Fix broken paths
        length = int(self.headers.get('Content-Length','0'))
        self.post_body = self.rfile.read(length)
        self.post_body = str(unquote(self.post_body.decode('utf-8'))) # URL decode
        self.post_body = self.post_body[len(PARAMETER):] # Strip of the artificial parameter
        if PARAMETER != '' and self.post_body[:len(PARAMETER)] == PARAMETER:
            self.post_body = self.post_body[:-1] if '&' == self.post_body[-1] else self.post_body  # Strip off last & if parameter provided
        response = self.ws_request(self.path, self.post_body)
        self.http_response(response)

    def do_GET(self):
        self.path = '/'+self.path if self.path[0] != '/' else self.path # Fix broken paths
        response = self.ws_request(self.path, '')
        self.http_response(response)

    def http_response(self, response):
        """Analyze websocket response and send http response to a client"""

        if isinstance(response, (int, dict)):
            if response == 404:
                self.send_response(404)
                self.end_headers()
                return
            # elif response in (0, 3):
            #     response = ''
            else:
                self.send_response(500)
                self.end_headers()
                self.wfile.write('Web Socket error'.encode())
                return

        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        try:
            self.wfile.write(bytearray(response, 'utf-8'))
        except BrokenPipeError as error:
            print('[-] Client disconnected. '+str(error))

    def ws_request(self, url, content):
        """Send web socket request based on HTTP request"""

        global TARGET, SECURE, PROXY, DELAY, CONNECTION, CONN_START, KEEP
        # Prepare proxy if provided
        if PROXY:
            proxy = self.proxy_prepare(PROXY)
        else:
            proxy = None

        # Prepare headers
        headers = self.parse_headers(self.headers)

        # Get target from Host header if not provided
        if TARGET is None:
            target = self.headers.get('Host')
            # If non of the targets provided return error
            if target is None:
                print('[-] Target was not specified')
                return {'error': 'Target was not specified'}
        else:
            target = TARGET

        # Check if correct prefix is provided
        if 'ws://' != target[:5] and 'wss://' != target[:6]:
            error = 'Protocol not supported. Target {} has to have ws:// or wss:// protocol specified'.format(target)
            print('[-] {}'.format(error))
            return {'error': error}

        if 'wss://' == target[:6]:
            if SECURE:
                context={}
            else:
                context = {'cert_reqs': ssl.CERT_NONE, 'check_hostname': False}
        else:
            context = {}

        if CONNECTION is not None and CONNECTION.connected and datetime.now() - CONN_START > timedelta(seconds=KEEP):
            CONNECTION.close()

        if CONNECTION is None or not CONNECTION.connected:
            try:
                if proxy:
                    CONNECTION = create_connection('{}{}'.format(target, url), http_proxy_host=proxy[0], http_proxy_port=proxy[1], sslopt=context, header=headers)
                    CONN_START = datetime.now()
                    sleep(DELAY)
                else:
                    CONNECTION = create_connection('{}{}'.format(target, url), sslopt=context, header=headers)
                    CONN_START = datetime.now()
                    sleep(DELAY)
            except _exceptions.WebSocketBadStatusException as error:
                if error.status_code == 404:
                    return 404
                print('[-] Cannot connect to the host. {}'.format(error))
                return {'error': error}
            except _exceptions.WebSocketAddressException as error:
                print('[-] Address exception: {}'.format(error))
                return {'error': error}
            except _exceptions.WebSocketConnectionClosedException as error:
                print('[-] {}'.format(error))
                return {'error': error}
            except ConnectionRefusedError as error:
                print('[-] Cannot connect to host or proxy. {}'.format(error))
                return {'error': error}
            except ssl.SSLError as error:
                print('[-] SSL Error: {}'.format(error))
                return {'error': error}

        CONNECTION.send(content)
        response = CONNECTION.recv()
        # CONNECTION.close()
        return response

    def proxy_prepare(self, proxy=None):
        if proxy is None:
            return None
        if proxy.find('://') != -1:
            if 'http://' != proxy[:7]:
                print('[-] Only HTTP proxy is supported. Skipping proxy.')
                return None
            proxy = proxy[proxy.find('://')+3:]
        if ':' in proxy:
            port = int(proxy.split(':')[1])
        else:
            port = 8080
        host = proxy.split(':')[0]
        return (host, port)

    def parse_headers(self, headers=None):
        if headers is None:
            return None

        prepared = []
        for header in headers:
            if header.lower() in ('host', 'content-length', 'content-type'):
                continue
            prepared.append('{}: {}'.format(header, headers[header]))

        return prepared
    
    def log_message(self, log_format, *args):
        print('{} - - [{}] {}'.format(self.address_string(), self.log_date_time_string(), log_format%args))
        if self.post_body != '' and VERBOSE:
            print('================== WS BODY START ==================\n{}\n==================  WS BODY END  =================='.format(self.post_body))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='HTTP2WebSocket is Python 3 Web Socket Proxy tool to translate HTTP traffic to WebSocket application. It allows to test WebSocket app with tools like sqlmap, dirb, commix. Headers sent by you will be passed to Web Socket application.')
    parser.add_argument('-l','--listen', help='Local port to listen to.', type=int, required=True)
    parser.add_argument('-t','--target', help='Your target WebSocket application (E.g.: ws://localhost:1234)')
    parser.add_argument('-K', '--keep', help='Keep the connection open for provided amount of seconds', type=int, default=3)
    parser.add_argument('-d', '--delay', help='The delay between opening a WS connection and sending a request', type=int, default=0)
    parser.add_argument('-P','--parameter', help='Artificial parameter for POST body. Actual content sent will be the value of this parameter. Some tools (ex: fimap) don\'t work with plain body without any parameters.')
    parser.add_argument('-v','--verbose', default=False, action='store_true', help='Shows HTTP POST body message.')
    parser.add_argument('-k','--insecure', default=False, action='store_true', help='Don\'t verify SSL certificate.')
    parser.add_argument('-p','--proxy', default=False, help='HTTP proxy URL')
    args = parser.parse_args()

    CONNECTION = None
    CONN_START = 0
    TARGET = args.target
    KEEP = args.keep
    DELAY = args.delay
    PARAMETER = args.parameter+'=' if args.parameter is not None else ''
    VERBOSE = args.verbose
    SECURE = not args.insecure
    PROXY = args.proxy

    try:
        args.listen = int(args.listen)
        server = HTTPServer(('', args.listen), proxyServer)
        print('HTTP2WebSocket started listening on port:', args.listen)
        server.serve_forever()
    except KeyboardInterrupt:
        print(' User stopped server. Stopping HTTP2WebSocket')
        server.socket.close()
