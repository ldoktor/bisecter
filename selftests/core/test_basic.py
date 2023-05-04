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
from unittest import mock
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

    def basic_workflow(self, args, condition, exp):
        """ Run basic bisection and compare it to expected results """
        bisect = bisecter.Bisections(args)
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

    def test_bisections(self):
        """ First-fail mode of the bisection """
        args = [list(range(10)), "abcdefghijklmno", list(range(0, 130, 10))]
        self.basic_workflow(args, lambda x: not(x[0] > 5 and x[1] > 3),
                            [6, 4, 0])
        # No matching (should not happen but is a valid input)
        self.basic_workflow(args, lambda _: False, [0, 0, 1])
        # Only 0, 0, 0 is matching
        self.basic_workflow(args, lambda x: x == [0, 0, 0], [0, 0, 1])
        # Single parameter affects bisection
        self.basic_workflow(args, lambda x: x[0] <= 1, [2, 0, 0])
        self.basic_workflow(args, lambda x: x[0] <= 2, [3, 0, 0])
        self.basic_workflow(args, lambda x: x[0] <= 3, [4, 0, 0])
        self.basic_workflow(args, lambda x: x[0] <= 4, [5, 0, 0])
        self.basic_workflow(args, lambda x: x[0] <= 5, [6, 0, 0])
        self.basic_workflow(args, lambda x: x[0] <= 6, [7, 0, 0])
        self.basic_workflow(args, lambda x: x[0] <= 7, [8, 0, 0])
        self.basic_workflow(args, lambda x: x[0] <= 8, [9, 0, 0])
        # Only last one is failing
        self.basic_workflow(args, lambda x: x[0] <= 9, [9, 14, 12])
        # Combination of parameters affect bisection together
        self.basic_workflow(args, lambda x: x[0] <= 5 and x[1] <= 3,
                            [0, 4, 0])
        self.basic_workflow(args,
                            lambda x: x[0] <= 5 and x[1] <= 3 and x[2] <= 7,
                            [0, 0, 8])
        # Combination of parameters affect bisection independently
        self.basic_workflow(args, lambda x: x[0] <= 5 or x[1] <= 3,
                            [6, 4, 0])
        self.basic_workflow(args,
                            lambda x: x[0] <= 5 or x[1] <= 3 or x[2] <= 7,
                            [6, 4, 8])
        # All goods
        self.basic_workflow(args, lambda _: True, [9, 14, 12])


class BisectionTest(unittest.TestCase):
    def test_value(self):
        bisect = bisecter.Bisection("asdf")
        self.assertEqual("f", bisect.value())
        bisect.reset()
        self.assertEqual("s", bisect.value())


class BisecterMockedTest(unittest.TestCase):
    def test_extended_args(self):
        def join_args(*args):
            return f'called with {args}'
        eargs = ['1,2,3', 'range(100,110,2)', 'url://some_page',
                 'beaker://Distro:-10']
        with mock.patch('bisecter.range_beaker', join_args):
            with mock.patch('bisecter.range_url', join_args):
                bisect = bisecter.Bisecter()
                # Only check the range_* functions are called, those features
                # are tested in test_utils
                self.assertEqual([['1', '2', '3'],
                                  ['100', '102', '104', '106', '108'],
                                  "called with ('url://some_page',)",
                                  "called with ('beaker://Distro:-10',)"],
                                  bisect._parse_extended_args(eargs))


class BisecterTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="bisecter-selftest")
        self.statefile = os.path.join(self.tmpdir, "statefile")
        self.bisect = f"{BISECTER} --state-file {self.statefile}"

    def test_basic_workflow(self):
        bisect = self.bisect
        out = subprocess.run(f"{bisect} start -E 'range(100)' "
                             "'range(100)' 'range(0,100,    1   )'",
                             capture_output=True, check=True, shell=True)
        self.assertIn(b"0 99 99", out.stdout)
        out = subprocess.run(f"{bisect} bad", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"0 0 99", out.stdout)
        out = subprocess.run(f"{bisect} good", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"0 49 99", out.stdout)
        out = subprocess.run(f"{bisect} bad", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"0 24 99", out.stdout)
        out = subprocess.run(f"{bisect} bad", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"0 12 99", out.stdout)
        out = subprocess.run(f"{bisect} bad", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"0 6 99", out.stdout)
        out = subprocess.run(f"{bisect} bad", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"0 3 99", out.stdout)
        out = subprocess.run(f"{bisect} skip", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"0 2 99", out.stdout)
        out = subprocess.run(f"{bisect} run {TEST_SH_PATH}",
                             capture_output=True, check=True, shell=True)
        self.assertIn(b"0 1 77", out.stdout)
        out = subprocess.run(f"{bisect} args", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"0 1 77", out.stdout)
        out = subprocess.run(f"{bisect} args -r -i 9-8-7", capture_output=True,
                             check=True, shell=True)
        self.assertIn(b"['9', '8', '7']", out.stdout)
        out = subprocess.run(f"{bisect} args -i 9999-999",
                             capture_output=True, check=False, shell=True)
        self.assertEqual(out.returncode, 255)
        self.assertIn(b"Incorrect id", out.stderr)
        out = subprocess.run(f"{bisect} id", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"0-1-77", out.stdout)
        out = subprocess.run(f"{bisect} log", capture_output=True, check=True,
                             shell=True)
        self.assertEqual(out.stdout.count(b'\n'), 21, "Incorrect number of "
                         f"lines in:\n{out.stdout}")
        out = subprocess.run(f"{bisect} good", capture_output=True, check=True,
                             shell=True)
        self.assertIn(b"Bisection complete", out.stdout)
        self.assertIn(b"0 1 77", out.stdout)
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
        out = subprocess.run(f"{bisect} start 1,1,1,1,FAILURE,1 0 0",
                             capture_output=True, check=True, shell=True)
        self.assertIn(b'1 0 0', out.stdout)
        out = subprocess.run(f"{bisect} run {TEST_SH_PATH}",
                             capture_output=True, check=False, shell=True)
        self.assertIn(b"returned 135, interrupting", out.stderr)
        out = subprocess.run(f"{bisect} log", capture_output=True, check=True,
                             shell=True)
        self.assertEqual(out.stdout.count(b'\n'), 6, "Incorrect number of "
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
        self.assertIn(b'1 5', out.stdout)
        self.assertNotIn(b"WARNING", out.stderr)
        subprocess.run(f"{bisect} reset", capture_output=True, check=True,
                       shell=True)
        out = subprocess.run(f"{bisect} start --from-yaml {yaml_path} 1,2,3",
                             capture_output=True, check=True, shell=True)
        self.assertIn(b'1 5', out.stdout)
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
