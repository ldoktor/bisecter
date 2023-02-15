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
import shutil
import subprocess
import sys
import tempfile
import unittest

import bisecter

try:
    import yaml
    YAML_INSTALLED = True
    del yaml
except ImportError:
    YAML_INSTALLED = False

BISECTER = os.environ.get("UNITTEST_BISECTER_CMD",
                          f"{sys.executable} -m bisecter")
TEST_SH_PATH = os.path.join(os.path.dirname(__file__), "assets",
                            "test.sh")


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

    def basic_workflow(self, args, condition, exp, klass=bisecter.Bisections):
        """ Run basic bisection and compare it to expected results """
        bisect = klass(args)
        try:
            current = bisect.current()
            while current is not None:
                if condition(current):
                    #import pydevd; pydevd.settrace("127.0.0.1", True, True)
                    current = bisect.good()
                else:
                    #import pydevd; pydevd.settrace("127.0.0.1", True, True)
                    current = bisect.bad()
            act = bisect.current()
            self.assertEqual(exp, act)
            self.check_log_for_duplicities(bisect)
            bisect.value()
            return act
        except:
            print("bisect.log()")
            print(bisect.log())
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

    def test_down_bisections(self):
        """ First-fail mode of the bisection """
        args = [list(range(10)), "abcdefghijklmno", list(range(0, 130, 10))]
        self.basic_workflow(args, lambda x: not(x[0] > 5 and x[1] > 3),
                            [5, 3, 0],
                            bisecter.DownBisections)
        # No matching (should not happen but is a valid input)
        self.basic_workflow(args, lambda x: False, [0, 0, 0],
                            bisecter.DownBisections)
        # Only 0, 0, 0 is matching
        self.basic_workflow(args, lambda x: x == [0, 0, 0], [0, 0, 0],
                            bisecter.DownBisections)
        # Single parameter affects bisection
        self.basic_workflow(args, lambda x: x[0] <= 1, [1, 0, 0],
                            bisecter.DownBisections)
        self.basic_workflow(args, lambda x: x[0] <= 2, [2, 0, 0],
                            bisecter.DownBisections)
        self.basic_workflow(args, lambda x: x[0] <= 3, [3, 0, 0],
                            bisecter.DownBisections)
        self.basic_workflow(args, lambda x: x[0] <= 4, [4, 0, 0],
                            bisecter.DownBisections)
        self.basic_workflow(args, lambda x: x[0] <= 5, [5, 0, 0],
                            bisecter.DownBisections)
        self.basic_workflow(args, lambda x: x[0] <= 6, [6, 0, 0],
                            bisecter.DownBisections)
        self.basic_workflow(args, lambda x: x[0] <= 7, [7, 0, 0],
                            bisecter.DownBisections)
        self.basic_workflow(args, lambda x: x[0] <= 8, [8, 0, 0],
                            bisecter.DownBisections)
        self.basic_workflow(args, lambda x: x[0] <= 9, [9, 0, 0],
                            bisecter.DownBisections)
        # Combination of parameters affect bisection
        self.basic_workflow(args, lambda x: x[0] <= 5 and x[1] <= 3,
                            [0, 3, 0],
                            bisecter.DownBisections)
        self.basic_workflow(args,
                            lambda x: x[0] <= 5 and x[1] <= 3 and x[2] <= 7,
                            [0, 0, 7],
                            bisecter.DownBisections)
        # All goods
        self.basic_workflow(args, lambda _: True, [9, 14, 12],
                            bisecter.DownBisections)


class BisectionTest(unittest.TestCase):
    def test_value(self):
        bisect = bisecter.Bisection("asdf")
        self.assertEqual("a", bisect.value())
        bisect.reset()
        self.assertEqual("s", bisect.value())

class BisecterTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="bisecter-selftest")
        self.statefile = os.path.join(self.tmpdir, "statefile")
        self.bisect = f"{BISECTER} --state-file {self.statefile}"

    def test_basic_workflow(self):
        bisect = self.bisect
        out = subprocess.run(f"{bisect} start -E 'range(100)' 'range(100)' "
                             "'range(0,100,    1   )'", capture_output=True,
                             check=True, shell=True)
        self.assertIn(b"49 0 0", out.stdout)
        out = subprocess.run(f"{bisect} bad", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"24 0 0", out.stdout)
        out = subprocess.run(f"{bisect} bad", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"12 0 0", out.stdout)
        out = subprocess.run(f"{bisect} bad", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"6 0 0", out.stdout)
        out = subprocess.run(f"{bisect} good", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"9 0 0", out.stdout)
        out = subprocess.run(f"{bisect} good", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"11 0 0", out.stdout)
        out = subprocess.run(f"{bisect} bad", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"10 0 0", out.stdout)
        out = subprocess.run(f"{bisect} bad", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"9 49 0", out.stdout)
        out = subprocess.run(f"{bisect} skip", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"9 48 0", out.stdout)
        out = subprocess.run(f"{bisect} run {TEST_SH_PATH}",
                             capture_output=True, check=True, shell=True)
        self.assertIn(b"9 3 76", out.stdout)
        out = subprocess.run(f"{bisect} args", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"9 3 76", out.stdout)
        out = subprocess.run(f"{bisect} args -r 9-8-7", capture_output=True,
                             check=True, shell=True)
        self.assertIn(b"['9', '8', '7']", out.stdout)
        out = subprocess.run(f"{bisect} args 9999-999",
                             capture_output=True, check=False, shell=True)
        self.assertEqual(out.returncode, 255)
        self.assertIn(b"Incorrect id", out.stderr)
        out = subprocess.run(f"{bisect} id", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"9-3-76", out.stdout)
        out = subprocess.run(f"{bisect} log", capture_output=True, check=True,
                             shell=True)
        self.assertEqual(out.stdout.count(b'\n'), 112, "Incorrect number of "
                         f"lines in:\n{out.stdout}")
        out = subprocess.run(f"{bisect} good", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"Bisection complete", out.stdout)
        self.assertIn(b"9 3 76", out.stdout)
        out = subprocess.run(f"{bisect} start foo", capture_output=True,
                             check=False, shell=True)
        self.assertEqual(out.returncode, 255)
        self.assertIn(b"already in progress", out.stderr)
        _ = subprocess.run(f"{bisect} reset", capture_output=True,
                           check=True, shell=True)
        out = subprocess.run(f"{bisect} reset", capture_output=True,
                             check=True, shell=True)
        self.assertIn(b"No bisection in", out.stderr)
        self.assertFalse(os.path.exists(self.statefile))
        out = subprocess.run(f"{bisect} non-existing-command",
                             capture_output=True, check=False, shell=True)
        self.assertEqual(out.returncode, 2, out)

    def test_run_with_interruption(self):
        bisect = self.bisect
        out = subprocess.run(f"{bisect} start 1,1,1,1,1,FAILURE 0 0",
                             capture_output=True, check=True, shell=True)
        self.assertIn(b'1 0 0', out.stdout)
        out = subprocess.run(f"{bisect} run {TEST_SH_PATH}",
                             capture_output=True, check=False, shell=True)
        self.assertIn(b"returned 135, interrupting", out.stderr)
        out = subprocess.run(f"{bisect} log", capture_output=True, check=True,
                             shell=True)
        self.assertEqual(out.stdout.count(b'\n'), 2, "Incorrect number of "
                         f"lines in:\n{out.stdout}")

    def test_incorrect_files(self):
        bisect = self.bisect
        out = subprocess.run(f"{bisect}{os.path.sep}bad-location start foo",
                             capture_output=True, check=False, shell=True)
        self.assertIn(b"Failed to open", out.stderr, out)
        self.assertEqual(out.returncode, 255, out)
        out = subprocess.run(f"{bisect} args",
                             capture_output=True, check=False, shell=True)
        self.assertEqual(out.returncode, 255, out)
        self.assertIn(b"Failed to open", out.stderr, out)
        self.assertIn(b" start' first", out.stderr, out)
        with open(self.statefile, 'wb') as state:
            state.write(b'malformed state file')
        out = subprocess.run(f"{bisect} args",
                             capture_output=True, check=False, shell=True)
        self.assertEqual(out.returncode, 255, out)
        self.assertIn(b"Failed to read bisecter state", out.stderr, out)
        os.remove(self.statefile)

    @unittest.skipUnless(YAML_INSTALLED, "PyYAML not installed")
    def test_yaml(self):
        bisect = self.bisect
        yaml_path = os.path.join(self.tmpdir, 'args.yml')
        out = subprocess.run(f"{bisect} start --from-yaml {yaml_path}",
                             capture_output=True, check=False, shell=True)
        self.assertEqual(out.returncode, 255, out)
        self.assertIn(b"Failed to read", out.stderr, out)
        with open(yaml_path, 'wb') as yaml_fd:
            yaml_fd.write(b"'incorrect yaml")
        out = subprocess.run(f"{bisect} start --from-yaml {yaml_path}",
                             capture_output=True, check=False, shell=True)
        self.assertEqual(out.returncode, 255, out)
        self.assertIn(b"Failed to load", out.stderr, out)
        with open(yaml_path, 'wb') as yaml_fd:
            yaml_fd.write(b"[[1, 2, 3], [4, 5]]")
        out = subprocess.run(f"{bisect} start --from-yaml {yaml_path}",
                             capture_output=True, check=True, shell=True)
        self.assertIn(b'2 4', out.stdout)
        self.assertNotIn(b"WARNING", out.stderr)
        subprocess.run(f"{bisect} reset", capture_output=True, check=True,
                       shell=True)
        out = subprocess.run(f"{bisect} start --from-yaml {yaml_path} 1,2,3",
                             capture_output=True, check=True, shell=True)
        self.assertIn(b'2 4', out.stdout)
        self.assertIn(b"WARNING", out.stderr)
        subprocess.run(f"{bisect} reset", capture_output=True, check=True,
                       shell=True)
        with open(yaml_path, 'wb') as yaml_fd:
            yaml_fd.write(b"[4, 5]")
        out = subprocess.run(f"{bisect} start --from-yaml {yaml_path}",
                             capture_output=True, check=False, shell=True)
        self.assertIn(b"Failed to parse arguments", out.stderr)
        self.assertEqual(out.returncode, 255, out)

    def tearDown(self):
        if self.tmpdir:
            shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
