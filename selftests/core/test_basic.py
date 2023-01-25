#!/bin/env python3
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2020
# Author: Lukas Doktor <ldoktor@redhat.com>

import os
import re
import tempfile
from unittest import mock
import unittest

import bisecter
import shutil


class UnitTest(unittest.TestCase):
    def basic_workflow(self, args, condition, exp):
        bisect = bisecter.Bisections(args)
        try:
            current = bisect.current()
            while current is not None:
                if condition(current):
                    current = bisect.good()
                else:
                    current = bisect.bad()
            act = bisect.last_good
            self.assertEqual(exp, act)
            return act
        except:
            print("bisect.log()")
            print(bisect.log())
            print(f"bisect.last_good: {bisect.last_good}")
            raise

    def test_basic_workflows(self):
        args = [list(range(10)), "abcdefghijklmno", list(range(0, 130, 10))]
        # No matching (should not happen but is a valid input)
        self.basic_workflow(args, lambda x: False, [0, 0, 0])
        # Only 0, 0, 0 is matching
        self.basic_workflow(args, lambda x: x == [0, 0, 0], [0, 0, 0])
        # Single parameter affects bisection
        self.basic_workflow(args, lambda x: x[0] <= 1, [1, 14, 12])
        self.basic_workflow(args, lambda x: x[0] <= 2, [2, 14, 12])
        self.basic_workflow(args, lambda x: x[0] <= 3, [3, 14, 12])
        self.basic_workflow(args, lambda x: x[0] <= 4, [4, 14, 12])
        self.basic_workflow(args, lambda x: x[0] <= 5, [5, 14, 12])
        self.basic_workflow(args, lambda x: x[0] <= 6, [6, 14, 12])
        self.basic_workflow(args, lambda x: x[0] <= 7, [7, 14, 12])
        self.basic_workflow(args, lambda x: x[0] <= 8, [8, 14, 12])
        self.basic_workflow(args, lambda x: x[0] <= 9, [9, 14, 12])
        self.basic_workflow(args, lambda x: True, [9, 14, 12])

'''
class PathTracker(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="runperf-selftest")

    def test_path_tracker(self):
        tracker = utils.ContextManager(mock.Mock())
        join = os.path.join
        self.assertEqual(None, tracker.get())
        self.assertRaises(RuntimeError, tracker.set, 0, "foo")
        tracker.set_root(self.tmpdir)
        self.assertEqual(self.tmpdir, tracker.get())
        tracker.set(0, "bar")
        self.assertEqual(join(self.tmpdir, "bar"), tracker.get())
        tracker.set(0, "foo")
        self.assertEqual(join(self.tmpdir, "foo"), tracker.get())
        tracker.set(3, "baz")
        self.assertEqual(join(self.tmpdir, "foo", "__NOT_SET__",
                              "__NOT_SET__", "baz"), tracker.get())
        tracker.set(1, "bar")
        self.assertEqual(join(self.tmpdir, "foo", "bar"), tracker.get())
        tracker.set(1, "baz")
        self.assertEqual(join(self.tmpdir, "foo", "baz"), tracker.get())
        tracker.set(2, "bar")
        self.assertEqual(join(self.tmpdir, "foo", "baz", "bar"), tracker.get())
        tracker.set(-1, "fee")
        self.assertEqual(join(self.tmpdir, "foo", "baz", "fee"), tracker.get())
        tracker.set(1, os.path.join(self.tmpdir, "foo", "another", "bar"))
        self.assertEqual(join(self.tmpdir, "foo", "another", "bar"),
                         tracker.get())
        tracker.set_level(1)
        self.assertEqual(join(self.tmpdir, "foo"), tracker.get())
        tracker.set_level(0)
        self.assertEqual(self.tmpdir, tracker.get())
        tracker.set_level(1)
        self.assertEqual(join(self.tmpdir, "__NOT_SET__"), tracker.get())

    def tearDown(self):
        if self.tmpdir:
            shutil.rmtree(self.tmpdir)

'''

if __name__ == '__main__':
    unittest.main()
