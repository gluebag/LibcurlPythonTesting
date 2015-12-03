
__author__ = 'gluebag'

import io
import mimetypes

import random
import pycurl
import netifaces
import HttpClientsArray


from tornado import gen
from TornadoCookieJar import TornadoCookieJar


class GlueHttp(object):

    setup_lock = None
    is_setup = False

    # INTERFACE CACHE
    interfaces = None

    # CLIENTS DICTIONARY
    clients = {}

    @staticmethod
    def add_client(key, number_of_classes=1, max_concurrent_per_class=1):

        if key is None:
            return False

        key = str(key)

        if key in GlueHttp.clients:
            return False

        GlueHttp.clients[key] = HttpClientsArray.HttpClientsArray(number_of_classes, max_concurrent_per_class)
        return True

    @staticmethod
    def get_random_network_interface():

        if GlueHttp.interfaces is None:
            adapters = netifaces.interfaces()
            white_list = []
            for x in adapters:
                if str(x).startswith('eth') or str(x).startswith('em'):
                    ip = netifaces.ifaddresses(x)
                    if ip is not None and 2 in ip:
                        white_list.append(x)

            GlueHttp.interfaces = white_list

        ret = random.choice(GlueHttp.interfaces)
        return ret

    def __init__(self, userAgent=None, printConsoleFunk=None):

        self.printConsole = printConsoleFunk
        self.Client = None
        self.Cookies = TornadoCookieJar()
        self.ConnectTimeout = 35.0
        self.RequestTimeout = 60.0
        self.FollowRedirects = False
        self.ProxyHost = None
        self.ProxyPort = None
        self.ProxyUsername = None
        self.ProxyPassword = None
        self.ValidateSslCertificates = False
        self.UserAgent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
        if userAgent:
            self.UserAgent = userAgent

    def setProxy(self, proxyString):

        self.ProxyHost = None
        self.ProxyPort = None
        self.ProxyUsername = None
        self.ProxyPassword = None
        if not proxyString:
            return

        proxyString = str(proxyString)
        if ':' not in proxyString:
            return

        proxyParts = proxyString.split(':')
        if len(proxyParts) < 2:
            return

        self.ProxyHost = str(proxyParts[0])
        self.ProxyPort = int(proxyParts[1])

        if len(proxyParts) < 4:
            return

        self.ProxyUsername = proxyParts[2]
        self.ProxyPassword = proxyParts[3]

    # Returns TRUE if we need to reissue out the request
    def response_middleware(self, callback, response):

        ret = False

        if response is not None:
            # Add cookies from response if possible
            self.Cookies.handleResponse(response)

            # Check for proxy timeout error if possible
            if response.error:
                errorAsString = str(response.error)
                if 'CurlError(599' in errorAsString:
                    response.timed_out = True
                elif 'Operation timed' in errorAsString or 'Proxy CONNECT aborted' in errorAsString:
                    response.timed_out = True
                elif 'Connection reset by peer' in errorAsString or 'Connection refused' in errorAsString:
                    response.timed_out = True
                elif 'transfer closed with outstanding read data remaining' in errorAsString:
                    response.timed_out = True
                elif 'Unknown SSL protocol error in connection to' in errorAsString:
                    response.timed_out = True
                elif 'wrong version number' in errorAsString:
                    response.timed_out = True
                elif 'Internal Server Error' in errorAsString:
                    response.timed_out = True
                    response.skype_fuckup = True

            if hasattr(response, 'code') and response.code is not None:
                code = str(response.code)
                if code == '0':
                    response.timed_out = True
                elif code == '599':
                    response.timed_out = True
                elif code == '429':
                    response.timed_out = True
                elif code == '502':
                    response.timed_out = True
                    response.skype_fuckup = True

            if hasattr(response, 'effective_url'):
                url = response.effective_url
                if 'gateway.messenger.live.com' in url:
                    if hasattr(response, 'headers') and 'ContextId' in response.headers:
                        contextId = str(response.headers['ContextId'])
                        if len(contextId) >= 1:
                            if 'tcid=' in contextId:
                                parts = contextId.split(',')
                                if len(parts) >= 2:
                                    server = parts[1]
                                    if 'server=' in server:
                                        server = server.split('=')[1]
                                        # SkypeHelpers.SkypeHelpers.track_msn_server(server)

        if not ret:
            callback(response)
        return ret

    @staticmethod
    def curlSetupCallback(curlObj):

        curlObj.setopt(pycurl.SSLVERSION, pycurl.SSLVERSION_TLSv1)
        curlObj.setopt(pycurl.DNS_CACHE_TIMEOUT, 0)
        curlObj.setopt(pycurl.MAXCONNECTS, 1)

        # CLEANUP FORBID REUSE / FRESH_CONNECT
        curlObj.setopt(pycurl.FRESH_CONNECT, 0)
        curlObj.setopt(pycurl.FORBID_REUSE, 0)

    @staticmethod
    def curlSetupCallbackFreshConnect(curlObj):

        curlObj.setopt(pycurl.SSLVERSION, pycurl.SSLVERSION_TLSv1)
        curlObj.setopt(pycurl.DNS_CACHE_TIMEOUT, 0)
        curlObj.setopt(pycurl.FRESH_CONNECT, 1)
        curlObj.setopt(pycurl.FORBID_REUSE, 1)

    @gen.coroutine
    def Get(self, url, callback, headers=None, override_timeout=None):

        if not headers:
            headers = {}

        cookiestring = self.Cookies.getCookieHeaderStringForUrl(url)
        if len(cookiestring) >= 1:
            headers['Cookie'] = cookiestring

        time_out = self.RequestTimeout
        if override_timeout is not None and int(override_timeout) >= 1:
            time_out = override_timeout

        curl_httpclient = None
        curl_prepare_cb = None

        if self.ProxyHost is not None:

            # use fresh connect on any proxy'd calls
            curl_prepare_cb = GlueHttp.curlSetupCallbackFreshConnect
            curl_httpclient = GlueHttp.clients['proxied'].get_next_client()

        else:

            curl_prepare_cb = GlueHttp.curlSetupCallback
            curl_httpclient = GlueHttp.clients['direct'].get_next_client()

        needs_reiussed = True
        while needs_reiussed:
            response = yield curl_httpclient.fetch(url, None, False, method='GET', headers=headers,
                           connect_timeout=self.ConnectTimeout, request_timeout=time_out,
                           follow_redirects=self.FollowRedirects, user_agent=self.UserAgent,
                           validate_cert=self.ValidateSslCertificates, proxy_host=self.ProxyHost,
                           proxy_port=self.ProxyPort, proxy_username=self.ProxyUsername, proxy_password=self.ProxyPassword,
                                             allow_ipv6=False, network_interface=GlueHttp.get_random_network_interface(),
                           prepare_curl_callback=curl_prepare_cb)
            needs_reiussed = self.response_middleware(callback, response)


    @gen.coroutine
    def Post(self, url, postData, callback, headers=None, override_timeout=None, use_fresh_connect=False):

        if not headers:
            headers = {}

        cookiestring = self.Cookies.getCookieHeaderStringForUrl(url)
        if len(cookiestring) >= 1:
            headers['Cookie'] = cookiestring

        time_out = self.RequestTimeout
        if override_timeout is not None and int(override_timeout) >= 1:
            time_out = override_timeout

        curl_httpclient = None
        curl_prepare_cb = None

        if self.ProxyHost is not None:

            # use fresh connect on any proxy'd calls
            curl_prepare_cb = GlueHttp.curlSetupCallbackFreshConnect
            curl_httpclient = GlueHttp.clients['proxied'].get_next_client()

        else:

            curl_prepare_cb = GlueHttp.curlSetupCallback
            curl_httpclient = GlueHttp.clients['direct'].get_next_client()

        needs_reiussed = True
        while needs_reiussed:
            response = yield curl_httpclient.fetch(url, None, False, method='POST', body=postData, headers=headers,
                           connect_timeout=self.ConnectTimeout, request_timeout=time_out,
                           follow_redirects=self.FollowRedirects, user_agent=self.UserAgent,
                           validate_cert=self.ValidateSslCertificates, proxy_host=self.ProxyHost,
                           proxy_port=self.ProxyPort, proxy_username=self.ProxyUsername, proxy_password=self.ProxyPassword,
                           allow_ipv6=False, network_interface=GlueHttp.get_random_network_interface(),
                           prepare_curl_callback=curl_prepare_cb)
            needs_reiussed = self.response_middleware(callback, response)

    @gen.coroutine
    def Put(self, url, postData, callback, headers=None, override_timeout=None):

        if not headers:
            headers = {}

        cookiestring = self.Cookies.getCookieHeaderStringForUrl(url)
        if len(cookiestring) >= 1:
            headers['Cookie'] = cookiestring

        time_out = self.RequestTimeout
        if override_timeout is not None and int(override_timeout) >= 1:
            time_out = override_timeout

        curl_httpclient = None
        curl_prepare_cb = None

        if self.ProxyHost is not None:

            # use fresh connect on any proxy'd calls
            curl_prepare_cb = GlueHttp.curlSetupCallbackFreshConnect
            curl_httpclient = GlueHttp.clients['proxied'].get_next_client()

        else:

            curl_prepare_cb = GlueHttp.curlSetupCallback
            curl_httpclient = GlueHttp.clients['direct'].get_next_client()

        needs_reiussed = True
        while needs_reiussed:
            response = yield curl_httpclient.fetch(url, None, False, method='PUT', body=postData, headers=headers,
                           connect_timeout=self.ConnectTimeout, request_timeout=time_out,
                           follow_redirects=self.FollowRedirects, user_agent=self.UserAgent,
                           validate_cert=self.ValidateSslCertificates, proxy_host=self.ProxyHost,
                           proxy_port=self.ProxyPort, proxy_username=self.ProxyUsername, proxy_password=self.ProxyPassword,
                                             allow_ipv6=False, network_interface=GlueHttp.get_random_network_interface(),
                           prepare_curl_callback=curl_prepare_cb)
            needs_reiussed = self.response_middleware(callback, response)

    @gen.coroutine
    def SolveCaptcha(self, username, password, captchaBytes, callback, override_timeout=None):

        headers = {}

        normalFields = [
            ('function', 'picture2'),
            ('username', username),
            ('password', password),
            ('pict_to', '0'),
            ('pict_type', '0'),
        ]
        fileFields = [
            ('pict', 'image.jpg', captchaBytes)
        ]
        postDataTuple = self.encode_multipart_formdata(normalFields, fileFields)
        url = 'http://poster.de-captcher.com'
        headers['Content-Type'] = postDataTuple[0]

        time_out = self.RequestTimeout
        if override_timeout is not None and int(override_timeout) >= 1:
            time_out = override_timeout

        curl_httpclient = None
        curl_prepare_cb = None

        if self.ProxyHost is not None:

            # use fresh connect on any proxy'd calls
            curl_prepare_cb = GlueHttp.curlSetupCallbackFreshConnect
            curl_httpclient = GlueHttp.clients['proxied'].get_next_client()

        else:

            curl_prepare_cb = GlueHttp.curlSetupCallback
            curl_httpclient = GlueHttp.clients['direct'].get_next_client()

        response = yield curl_httpclient.fetch(url, None, False, method='POST', body=postDataTuple[1], headers=headers,
                       connect_timeout=self.ConnectTimeout, request_timeout=time_out,
                       follow_redirects=self.FollowRedirects, user_agent=self.UserAgent,
                       validate_cert=self.ValidateSslCertificates, proxy_host=None,
                       proxy_port=None, proxy_username=None, proxy_password=None,
                                         allow_ipv6=False, network_interface=GlueHttp.get_random_network_interface(),
                       prepare_curl_callback=curl_prepare_cb)
        self.decaptcherMiddleWare(callback, response)
        # self.runLocked(call_me)

    def decaptcherMiddleWare(self, callback, response):

        solvedAs = ''
        if not response or response.code != 200:
            callback(solvedAs)
            return

        src = str(response.body)
        splits = src.split('|')
        if len(splits) < 6:
            callback(solvedAs)
            return

        solvedAs = splits[5]
        callback(solvedAs)


    def encode_multipart_formdata(self, fields, files):
        """
        fields is a sequence of (name, value) elements for regular form fields.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files
        Return (content_type, body) ready for httplib.HTTP instance
        """
        BOUNDARY = '--------------{}'.format(random.randrange(10000, 99999))
        CRLF = '\r\n'
        L = []
        for (key, value) in fields:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)
        for (key, filename, value) in files:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
            L.append('Content-Type: %s' % self.get_content_type(filename))
            L.append('')
            L.append(value)
        L.append('--' + BOUNDARY + '--')
        L.append('')
        s = io.BytesIO()
        for element in L:
            if type(element) is io.BytesIO:
                s.write(element.read())
            else:
                s.write(str(element))
            s.write(CRLF)
        body = s.getvalue()
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        return content_type, body

    def get_content_type(self, filename):
        return mimetypes.guess_type(filename)[0] or 'application/octet-stream'


