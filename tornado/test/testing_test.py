#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, with_statement

from tornado import gen, ioloop
from tornado.testing import AsyncTestCase, gen_test
from tornado.test.util import unittest

import functools
import os


class AsyncTestCaseTest(AsyncTestCase):
    def test_exception_in_callback(self):
        self.io_loop.add_callback(lambda: 1 / 0)
        try:
            self.wait()
            self.fail("did not get expected exception")
        except ZeroDivisionError:
            pass

    def test_subsequent_wait_calls(self):
        """
        This test makes sure that a second call to wait()
        clears the first timeout.
        """
        self.io_loop.add_timeout(self.io_loop.time() + 0.01, self.stop)
        self.wait(timeout=0.02)
        self.io_loop.add_timeout(self.io_loop.time() + 0.03, self.stop)
        self.wait(timeout=0.15)


class SetUpTearDownTest(unittest.TestCase):
    def test_set_up_tear_down(self):
        """
        This test makes sure that AsyncTestCase calls super methods for
        setUp and tearDown.

        InheritBoth is a subclass of both AsyncTestCase and
        SetUpTearDown, with the ordering so that the super of
        AsyncTestCase will be SetUpTearDown.
        """
        events = []
        result = unittest.TestResult()

        class SetUpTearDown(unittest.TestCase):
            def setUp(self):
                events.append('setUp')

            def tearDown(self):
                events.append('tearDown')

        class InheritBoth(AsyncTestCase, SetUpTearDown):
            def test(self):
                events.append('test')

        InheritBoth('test').run(result)
        expected = ['setUp', 'test', 'tearDown']
        self.assertEqual(expected, events)


class GenTest(AsyncTestCase):
    def setUp(self):
        super(GenTest, self).setUp()
        self.finished = False

    def tearDown(self):
        self.assertTrue(self.finished)
        super(GenTest, self).tearDown()

    @gen_test
    def test_sync(self):
        self.finished = True

    @gen_test
    def test_async(self):
        yield gen.Task(self.io_loop.add_callback)
        self.finished = True

    def test_timeout(self):
        # Set a short timeout and exceed it.
        @gen_test(timeout=0.1)
        def test(self):
            yield gen.Task(self.io_loop.add_timeout, self.io_loop.time() + 1)

        with self.assertRaises(ioloop.TimeoutError):
            test(self)

        self.finished = True

    def test_no_timeout(self):
        # A test that does not exceed its timeout should succeed.
        @gen_test(timeout=1)
        def test(self):
            yield gen.Task(self.io_loop.add_timeout, self.io_loop.time() + 0.1)

        test(self)
        self.finished = True

    def test_timeout_environment_variable(self):
        time = self.io_loop.time
        add_timeout = self.io_loop.add_timeout
        old_timeout = os.environ.get('TIMEOUT')
        try:
            os.environ['TIMEOUT'] = '0.1'

            @gen_test(timeout=0.5)
            def test_long_timeout(self):
                yield gen.Task(add_timeout, time() + 0.25)

            # Uses provided timeout of 0.5 seconds, doesn't time out.
            self.io_loop.run_sync(
                functools.partial(test_long_timeout, self))

            @gen_test(timeout=0.01)
            def test_short_timeout(self):
                yield gen.Task(add_timeout, time() + 1)

            # Uses environment TIMEOUT of 0.1, times out.
            with self.assertRaises(ioloop.TimeoutError):
                test_short_timeout(self)

            self.finished = True
        finally:
            if old_timeout is None:
                del os.environ['TIMEOUT']
            else:
                os.environ['TIMEOUT'] = old_timeout

if __name__ == '__main__':
    unittest.main()
