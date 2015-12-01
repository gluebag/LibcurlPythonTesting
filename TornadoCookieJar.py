
import requests.cookies
from urlparse import urlparse
import traceback
import urllib
import time
import Cookie

class TornadoCookieJar(object):

    _reserved = { "expires" : "expires",
               "path"        : "Path",
               "comment" : "Comment",
               "domain"      : "Domain",
               "max-age" : "Max-Age",
               "secure"      : "secure",
               "httponly"  : "httponly",
               "version" : "Version",
               }

    _weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    _monthname = [None,
                  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    _semispacejoin = '; '.join

    @staticmethod
    def _getdate(timestamp=0, weekdayname=_weekdayname, monthname=_monthname):
        from time import gmtime, time
        now = timestamp
        year, month, day, hh, mm, ss, wd, y, z = gmtime(now)
        return "%s, %02d-%3s-%4d %02d:%02d:%02d GMT" % \
               (weekdayname[wd], day, monthname[month], year, hh, mm, ss)

    @staticmethod
    def cookie_to_set_cookie_header(cookie):
        # Build up our result
        #
        result = []
        RA = result.append

        items = []

        name = ''
        value = ''

        properties = [method for method in dir(cookie)]
        for x in properties:
            if x.lower() == 'name':
                name = getattr(cookie, x)
                continue
            elif x.lower() == 'value':
                value = getattr(cookie, x)
                continue
            else:
                if x not in TornadoCookieJar._reserved:
                    continue
                items.append((x, getattr(cookie, x)))

        if len(name) < 1 or len(value) < 1:
            return None

        RA('%s=%s' % (name, urllib.quote_plus(value)))

        items.sort()

        for K,V in items:
            if V == "": continue

            # fix expires
            if K == 'expires' and V is None or len(str(V)) < 1:
                V = int(time.time() + 31536000) # 1 year
            if K == "expires" and type(V) == type(1):
                RA("%s=%s" % (TornadoCookieJar._reserved[K], TornadoCookieJar._getdate(V)))
            elif K == "max-age" and type(V) == type(1):
                RA("%s=%d" % (TornadoCookieJar._reserved[K], V))
            elif K == "secure":
                RA(str(TornadoCookieJar._reserved[K]))
            elif K == "httponly":
                RA(str(TornadoCookieJar._reserved[K]))
            else:
                RA("%s=%s" % (TornadoCookieJar._reserved[K], V))

        return TornadoCookieJar._semispacejoin(result)

    def __init__(self):

        self.jar = requests.cookies.RequestsCookieJar()


    def reset(self):

        self.jar = requests.cookies.RequestsCookieJar()

    def handleResponse(self, response):

        try:

            if response is None:
                return

            if not hasattr(response, 'headers'):
                return

            if response.headers is None:
                return

            lst = response.headers.get_list("Set-Cookie")

            for sc in lst:
                c = Cookie.SimpleCookie(sc)
                for morsel in c.values():

                    if morsel['max-age']:
                        morsel['max-age'] = int(morsel['max-age'])

                    cookie = requests.cookies.morsel_to_cookie(morsel)
                    self.jar.set_cookie(cookie)
        except Exception as e:
            print 'COOKIE JAR HANDLE RESPONSE ERROR'
            print e
            traceback.print_exc()

        #print self.jar

    def add_cookie_by_string(self, str):
        if str is not None and len(str) >= 1:
            c = Cookie.SimpleCookie(str)
            for morsel in c.values():

                if morsel['max-age']:
                    morsel['max-age'] = int(morsel['max-age'])

                cookie = requests.cookies.morsel_to_cookie(morsel)
                self.jar.set_cookie(cookie)


    def getCookieHeaderDictForUrl(self, url):

        details = urlparse(url)
        domain = details.netloc
        path = details.path

        dict = self.jar.get_dict()
        if not dict:
            return {}

        return dict

    def getCookieHeaderStringForUrl(self, url):

        details = urlparse(url)
        domain = details.netloc
        path = details.path

        #print 'urlparse: [host=%s, path=%s]' % (domain, path)

        dict = self.jar.get_dict()

        #print 'cookiedict: [%s]' % dict

        if not dict:
            return ''

        attrs = []
        for (key, value) in dict.items():
            attrs.append("%s=%s" % (key, value))
        return "; ".join(attrs)