try:
    from queue import Empty, Full, Queue
except ImportError:
    from Queue import Empty, Full, Queue
import time
import unittest
from time import monotonic

import stomp
from stomp.test.testutils import *


class MQ(object):
    def __init__(self):
        self.conn = stomp.Connection(get_default_host())
        self.conn.set_listener('', None)
        self.conn.connect('admin', 'password', wait=True)

    def send(self, topic, msg, persistent='true', retry=False):
        self.conn.send(destination="/topic/%s" % topic, body=msg,
                             persistent=persistent)


mq = MQ()


class TestThreading(unittest.TestCase):

    def setUp(self):
        """Test that mq sends don't wedge their threads.

        Starts a number of sender threads, and runs for a set amount of
        time. Each thread sends messages as fast as it can, and after each
        send, pops from a Queue. Meanwhile, the Queue is filled with one
        marker per second. If the Queue fills, the test fails, as that
        indicates that all threads are no longer emptying the queue, and thus
        must be wedged in their send() calls.

        """
        self.Q = Queue(10)
        self.Cmd = Queue()
        self.Error = Queue()
        self.clients = 20
        self.threads = []
        self.runfor = 20
        for i in range(0, self.clients):
            t = threading.Thread(name="client %s" % i,
                                 target=self.make_sender(i))
            t.setDaemon(1)
            self.threads.append(t)

    def tearDown(self):
        for t in self.threads:
            if not t.isAlive:
                print("thread", t, "died")
            self.Cmd.put('stop')
        for t in self.threads:
            t.join()
        print()
        print()
        errs = []
        while 1:
            try:
                errs.append(self.Error.get(block=False))
            except Empty:
                break
        print("Dead threads:", len(errs), "of", self.clients)
        etype = {}
        for ec, _, _ in errs:
            if ec in etype:
                etype[ec] += 1
            else:
                etype[ec] = 1
        for k in sorted(etype.keys()):
            print("%s: %s" % (k, etype[k]))
        mq.connection.disconnect()

    def make_sender(self, i):
        Q = self.Q
        Cmd = self.Cmd
        Error = self.Error

        def send(i=i, Q=Q, Cmd=Cmd, Error=Error):
            counter = 0
            print("%s starting" % i)
            try:
                while 1:
                    # print "%s sending %s" % (i, counter)
                    try:
                        mq.send('testclientwedge',
                                'Message %s:%s' % (i, counter))
                    except:
                        Error.put(sys.exc_info())
                        # thread will die
                        raise
                    else:
                        # print "%s sent %s" % (i, counter)
                        try:
                            Q.get(block=False)
                        except Empty:
                            pass
                        try:
                            if Cmd.get(block=False):
                                break
                        except Empty:
                            pass
                        counter += 1
            finally:
                print("final", i, counter)
        return send

    def test_threads_dont_wedge(self):
        for t in self.threads:
            t.start()
        start = monotonic()
        while monotonic() - start < self.runfor:
            try:
                self.Q.put(1, False)
                time.sleep(1.0)
            except Full:
                assert False, "Failed: 'request' queue filled up"
                print("passed")
