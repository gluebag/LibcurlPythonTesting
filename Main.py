__author__ = 'gluebag'

import GlueHttp
import tornado.ioloop
import tornado.log
import tornado.options

client = None

def main():

    print 'running main'

    # setup tornado loop
    loop = tornado.ioloop.IOLoop.instance()
    loop.set_blocking_log_threshold(0.5)

    # setup logging
    tornado_args = ['--log_file_prefix=tornado.log', '--logging=debug']
    tornado.options.parse_command_line(tornado_args)
    tornado.log.enable_pretty_logging()

    # setup shared gluehttp
    GlueHttp.GlueHttp.add_client('direct', 1, 1)

    # setup the single http client
    global client
    client = GlueHttp.GlueHttp()

    # setup periodic requester
    period = tornado.ioloop.PeriodicCallback(periodic_request, 500, io_loop=loop)
    period.start()

    loop.start()

def periodic_request():
    print 'sending request'
    url = 'http://159.203.108.58:1337/PYTHONBABY'
    client.Get(url, get_callback)

def get_callback(response):
    print response

main()