__author__ = 'gluebag'

import GlueHttp

def main():

    print 'running main'

    # setup shared gluehttp
    GlueHttp.GlueHttp.add_client('direct', 10, 10)

    # setup the single http client
    print 'sending request'
    url = 'http://159.203.108.58:1337/PYTHONBABY'
    url = 'http://www.google.com/'
    client = GlueHttp.GlueHttp()
    client.Get(url, get_callback)

def get_callback(response):
    print response

main()