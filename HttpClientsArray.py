__author__ = 'gluebag'

import tornado.httpclient
import tornado.curl_httpclient
import tornado.ioloop
import tornado.options
import tornado.log
import tornado.concurrent
import threading

class HttpClientsArray(object):

    def __init__(self, number_of_clients, number_of_concurrent_per):

        tornado.httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")

        self.clients = []

        self.client_index = 0

        self.client_lock = threading.Lock()

        for i in range(number_of_clients):
            self.clients.append(tornado.curl_httpclient.CurlAsyncHTTPClient(tornado.ioloop.IOLoop.instance(), force_instance=True, max_clients=number_of_concurrent_per))

    def get_next_client(self):

        ret = None

        self.client_lock.acquire()

        try:
            if self.client_index >= len(self.clients):
                self.client_index = 0

            ret = self.clients[self.client_index]

            self.client_index += 1

        except Exception as e:
            raise e
        finally:
            self.client_lock.release()

        return ret
