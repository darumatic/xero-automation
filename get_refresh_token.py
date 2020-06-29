#!/usr/bin/env python

import argparse
import os
import sys
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from requests_oauthlib import OAuth2Session

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
PORT_NUMBER = 3000
REDIRECT_URI = 'http://localhost:' + str(PORT_NUMBER)
SCOPE = ['offline_access', 'projects', 'openid', 'accounting.contacts', ]

client_id = ''
client_secret = ''
server_state = True


class oauth_callback_handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global client_id
        global client_secret
        global server_state

        if (not self.path.startswith("/?")):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            return

        callback_url = REDIRECT_URI + self.path
        token = oauth.fetch_token('https://identity.xero.com/connect/token', authorization_response=callback_url, client_secret=client_secret)
        connections = oauth.get("https://api.xero.com/connections").json()
        if len(connections) == 0:
            print 'Error, no connections.'
            return

        print "TENENT_ID:%s" % connections[0]['tenantId']
        print "REFRESH_TOKEN:%s" % token['refresh_token'],

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write("<html>Success! Checkout console output.</html>")
        self.wfile.close()
        server_state = False


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.realpath(__file__))

    parser = argparse.ArgumentParser("Get Xero refersh token")
    parser.add_argument('--client-id', type=str, required=True)
    parser.add_argument('--client-secret', type=str, required=True)

    args = parser.parse_args(sys.argv[1:])
    client_id = args.client_id
    client_secret = args.client_secret

    oauth = OAuth2Session(args.client_id, redirect_uri=REDIRECT_URI, scope=SCOPE)
    authorization_url, state = oauth.authorization_url('https://login.xero.com/identity/connect/authorize', access_type="offline", prompt="select_account")

    print "Please open the following URL in your browser:"
    print authorization_url
    server = HTTPServer(('', PORT_NUMBER), oauth_callback_handler)
    while server_state:
        server.handle_request()
