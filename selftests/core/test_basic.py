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


class BisectionsTest(unittest.TestCase):

    def check_log_for_duplicities(self, bisect):
        """ Check the internal Bisections._log for duplicate entries """
        log = bisect._log       # pylint: disable=W0212
        unique = set("-".join(str(ident) for ident in _.identifier)
                    for _ in log)
        self.assertEqual(len(unique), len(log), "Some variant was tested "
                         f"multiple times\n{unique}\n\n\n{log}")
        if len(unique) != len(log):
            raise Exception("Variant tested multiple times!")

    def basic_workflow(self, args, condition, exp):
        """ Run basic bisection and compare it to expected results """
        bisect = bisecter.Bisections(args)
        try:
            current = bisect.current()
            while current is not None:
                if condition(current):
                    current = bisect.good()
                else:
                    current = bisect.bad()
            act = bisect.current()
            self.assertEqual(exp, act)
            self.check_log_for_duplicities(bisect)
            bisect.value()
            return act
        except:
            print("bisect.log()")
            print(bisect.log())
            #print(f"bisect.last_good: {bisect.last_good}")
            raise

    def test_basic_workflows(self):
        """ Basic bisect workflow """
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
        # Combination of parameters affect bisection
        self.basic_workflow(args, lambda x: x[0] <= 5 and x[1] <= 3,
                            [5, 3, 12])
        self.basic_workflow(args,
                            lambda x: x[0] <= 5 and x[1] <= 3 and x[2] <= 7,
                            [5, 3, 7])
        # All goods
        self.basic_workflow(args, lambda _: True, [9, 14, 12])

    def test_value(self):
        """Ensures the reported values are correct"""
        args = [list(range(10)), "abcdefghijklmno", [0, 0, 0, 0, 1, 1, 2]]
        bisect = bisecter.Bisections(args)
        self.assertEqual([4, "a", 0], bisect.value())
        bisect.good()
        self.assertEqual([7, "a", 0], bisect.value())
        bisect.bad()
        self.assertEqual([6, "a", 0], bisect.value())
        bisect.good()
        self.assertEqual([6, "h", 0], bisect.value())
        bisect.bad()
        self.assertEqual([6, "d", 0], bisect.value())
        bisect.good()
        self.assertEqual([6, "f", 0], bisect.value())
        bisect.good()
        self.assertEqual([6, "g", 0], bisect.value())
        bisect.good()
        self.assertEqual([6, "g", 0], bisect.value())
        bisect.good()
        self.assertEqual([6, "g", 1], bisect.value())
        # Second to last bisection reports 4th element
        self.assertEqual([6, 6, 4], bisect.bad())
        self.assertEqual([6, "g", 1], bisect.value())
        # Last correct bisection reports None
        self.assertEqual(None, bisect.bad())
        # And the value should be the last good one
        self.assertEqual([6, "g", 0], bisect.value())
        # Repeating bad or good should not affect the bisection further
        self.assertEqual(None, bisect.bad())
        self.assertEqual([6, "g", 0], bisect.value())
        self.assertEqual(None, bisect.good())
        self.assertEqual([6, "g", 0], bisect.value())
        self.assertEqual([1, "b", 0], bisect.value([1,1,1]))
        self.assertEqual([7, "f", 2], bisect.value([7,5,-1]))
        self.assertRaises(IndexError, bisect.value, [1,1,100])

    def test_skip(self):
        args = [list(range(10)), "abcdefghijklmno", [0, 0, 0, 0, 1, 1, 2]]
        bisect = bisecter.Bisections(args)
        for action, exp in [(bisect.skip, [3, 0, 0]),
                            (bisect.skip, [5, 0, 0]),
                            (bisect.skip, [2, 0, 0]),
                            (bisect.skip, [6, 0, 0]),
                            (bisect.skip, [1, 0, 0]),
                            (bisect.skip, [7, 0, 0]),
                            (bisect.skip, [0, 7, 0]),
                            (bisect.good, [0, 11, 0]),
                            (bisect.skip, [0, 10, 0]),
                            (bisect.bad, [0, 9, 0]),
                            (bisect.skip, [0, 8, 0]),
                            (bisect.skip, [0, 7, 3]),
                            (bisect.good, [0, 7, 5]),
                            (bisect.bad, [0, 7, 4]),
                            (bisect.skip, [0, 7, 3]),]:
            action()
            self.assertEqual(exp, bisect.current(), f"{exp} != {bisect.value()}"
                             f"\n\n{bisect.log()}")
        self.assertEqual(None, bisect.good())
        self.assertEqual(None, bisect.bad())
        self.assertEqual(None, bisect.skip())

    def test_steps(self):
        args = [list(range(10)), "abcdefghijklmno", [0, 0, 0, 0, 1, 1, 2]]
        bisect = bisecter.Bisections(args)
        self.assertEqual(11, bisect.steps_left())
        self.assertEqual(31, bisect.variants_left())
        bisect.good()
        self.assertEqual(10, bisect.steps_left())
        self.assertEqual(26, bisect.variants_left())
        bisect.bad()
        self.assertEqual(9, bisect.steps_left())
        self.assertEqual(24, bisect.variants_left())
        bisect.bad()
        bisect.bad()
        bisect.bad()
        self.assertEqual(6, bisect.steps_left())
        self.assertEqual(14, bisect.variants_left())
        bisect.good()
        bisect.good()
        bisect.good()
        self.assertEqual(3, bisect.steps_left())
        self.assertEqual(6, bisect.variants_left())
        bisect.bad()
        self.assertEqual(2, bisect.steps_left())
        self.assertEqual(3, bisect.variants_left())
        bisect.bad()
        self.assertEqual(0, bisect.steps_left())
        self.assertEqual(0, bisect.variants_left())
        bisect.good()
        self.assertEqual(0, bisect.steps_left())
        self.assertEqual(0, bisect.variants_left())


class BisectionTest(unittest.TestCase):
    def test_value(self):
        bisect = bisecter.Bisection("asdf")
        self.assertEqual("a", bisect.value())
        bisect.reset()
        self.assertEqual("s", bisect.value())

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
