__author__ = 'gluebag'

def main():
    print 'running main'

main()

import pycurl
import tornado.gen
import tornado.ioloop
import tornado.log
import tornado.options
import sys
import resource
import GlueHttp
import math
import Queue
from tornado.process import fork_processes, task_id, Subprocess

import bugsnag
from guppy import hpy
from pprint import pprint
from tornado.httpclient import AsyncHTTPClient


# bugsnag.configure(
#  api_key="39652f568a19a0fea9c81c205e0eb113",
#  project_root="/root/GluePlayground",
# )


# obj = GlueHttp.GlueHttp()
# que = Queue.Queue()
# for x in range(5):
#     que.put(x)
# print 'Main before forking: [%s]' % obj
#



# item = que.get()
# print '[%s]: %s' % (id, item)
# exit(0)


# tornado.httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
# GlueHttp.GlueHttp.setup(0, classes, max_concurrent, ioloop)
# print 'MainIOLoop: [%s]' % ioloop
# GlueHttp.GlueHttp.setup_pool(classes, max_concurrent)

fetched = 0

def gotResponse(response):
    print response
    global fetched
    fetched += 1
    print fetched


def callIt(max_requests):

    url = 'http://gluetest.com:3000/heythere'
    # url = 'https://login.skype.com/login?method=skype&client_id=578134&redirect_uri=https%3A%2F%2Fweb.skype.com'

    for x in range(max_requests):
        c = GlueHttp.GlueHttp()
        c.RequestTimeout = 3600.0
        c.ConnectTimeout = 3600.0
        #c.GetUsingChild(url, gotResponse)
        c.Get(url, gotResponse)
        if x % 10000 == 0:
            print 'qued up: [%s]' % x

        #if x % 10000 == 0:
        #    hp = hpy()
        #    print hp.heap()

        #print 'RESULT FROM CALLIT: [%s]' % result


if __name__ == '__main__':

    args = sys.argv
    args.append('--log_file_prefix=logs/tornado.log')
    # args.append("--log_to_stderr")
    # args.append('--logging=debug')
    tornado.options.parse_command_line(args)
    tornado.log.enable_pretty_logging()
    loop = tornado.ioloop.IOLoop.instance()
    loop.set_blocking_log_threshold(0.5)

    forks = 5
    classes = math.trunc(25 / forks)
    max_concurrent = math.trunc(4000 / forks)
    max_requests = math.trunc(1 / forks)

    if classes < 1:
        classes = 1
    if max_concurrent < 1:
        max_concurrent = 1
    if max_requests < 1:
        max_requests = 1

    # test mine
    classes = 100
    max_concurrent = 2000
    max_requests = 200000
    GlueHttp.GlueHttp.setup(0, classes, max_concurrent, loop)
    loop.add_callback(callIt, max_requests)
    print 'starting loop'
    loop.start()
    print 'done'

    #tornado.ioloop.IOLoop.instance().add_callback(callIt, max_requests)
    #tornado.ioloop.IOLoop.instance().set_blocking_log_threshold(0.5)
    #tornado.ioloop.IOLoop.instance().start()

    import time
    while True:
        time.sleep(1)
    exit(0)




    id = fork_processes(forks, max_restarts=100)
    print id
    if id == 0:
        print 'I\'m the parent'
        tornado.ioloop.IOLoop.instance().set_blocking_log_threshold(0.5)
        tornado.ioloop.IOLoop.instance().start()
    else:
        print 'child %s starting...' % id
        print '%s, %s' % (classes,max_concurrent)
        clients = []
        GlueHttp.GlueHttp.setup(0, classes, max_concurrent, tornado.ioloop.IOLoop.instance(), clients)
        callIt(max_requests)