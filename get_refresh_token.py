import os
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from requests_oauthlib import OAuth2Session

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
import json

server_state = True


class oauth_callback_handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global server_state
        if (not self.path.startswith("/?")):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            return

        print self.path
        callback_url = REDIRECT_URI + self.path
        token = oauth.fetch_token('https://identity.xero.com/connect/token', authorization_response=callback_url, client_secret=CLIENT_SECRET)
        print "============== The refresh token:"
        print token['refresh_token']

        connections = oauth.get("https://api.xero.com/connections").json()
        print "============== Connections:"
        print json.dumps(connections)

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write("<html>Success</html>")
        self.wfile.close()

        server_state = False


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.realpath(__file__))

    CLIENT_ID = '1744C5B5478644999D632BC16B3D7D7C'
    CLIENT_SECRET = open(os.path.join(current_dir, "XERO_CLIENT_SECRET")).read().strip()
    PORT_NUMBER = 3000
    REDIRECT_URI = 'http://localhost:' + str(PORT_NUMBER)
    SCOPE = ['offline_access', 'projects', 'openid', 'accounting.contacts', ]

    oauth = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPE)
    authorization_url, state = oauth.authorization_url('https://login.xero.com/identity/connect/authorize', access_type="offline", prompt="select_account")

    print "============== Open the following URL in browser:"
    print authorization_url

    server = HTTPServer(('', PORT_NUMBER), oauth_callback_handler)
    while server_state:
        server.handle_request()
