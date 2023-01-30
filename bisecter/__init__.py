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
# Copyright: Red Hat Inc. 2023
# Author: Lukas Doktor <ldoktor@redhat.com>
"""
Example usage:

bisecter start '["some", "values"]' '["another", "values"]'
my_script "$(bisecter args)" $(bisecter id)
bisecter good
my_script "$(bisecter args)" $(bisecter id)
bisecter bad
...
bisecter log
bisecter reset

bisecter start '["some", "values"]' '["another", "values"]'
bisecter run my_script
bisecter log
bisecter reset
"""

import argparse
import ast
import dataclasses
import enum
import math
import os
import pickle
import pipes
import re
import subprocess
import sys


class BisectionStatus(enum.Enum):
    """Bisection status"""
    GOOD = 0
    BAD = 1
    SKIP = 125


@dataclasses.dataclass
class BisectionLogEntry:
    """Log entry"""
    status: BisectionStatus
    identifier: list

    def __str__(self):
        return (f"{self.status.name:4s} "
                f"{'-'.join(str(_) for _ in self.identifier)}")

    def __repr__(self):
        return (f"{self.status.name:4s} "
                f"{'-'.join(str(_) for _ in self.identifier)}")


class Bisection:
    """
    Object to keep track of a single bisection
    """
    current = None
    _good = None
    _bad = None
    _last_good = 0

    def __init__(self, values):
        self._values = values
        self._skips = []
        self.current = 0

    def value(self, index=None):
        """Value associated to the ``index`` value (by default current one)"""
        if index is not None:
            return self._values[index]
        return self._values[self.current]

    def _update_current(self):
        self.current = (self._good + self._bad) // 2

    def good(self):
        """Mark the current step as good (go to right)"""
        self._last_good = self.current
        new = self.current + 1
        # We iterate over multiple arrays and can not be sure the last
        # one of each is bad
        if (self._bad <= new and
                not new == len(self._values) - 1):
            self.reset(self._last_good, self._last_good)
            return None
        self._good = new
        self._update_current()
        return self.current

    def bad(self):
        """Mark the current step as bad (go to left)"""
        if self.current <= self._good:
            self.reset(self._last_good, self._last_good)
            return None
        self._bad = self.current
        self._update_current()
        if self.current <= 0:
            self.reset(self._last_good, self._last_good)
            return None
        return self.current

    def skip(self):
        """Mark the current step as skip (untestable)"""
        self._skips.append(self.current)
        offset = -1
        new = (self._good + self._bad) // 2 + offset
        # We iterate over multiple arrays and can not be sure the last
        # one of each is bad
        if new < self._good or (new >= self._bad and
                                 new != (len(self._values) - 1)):
            self.reset(self._last_good, self._last_good)
            return None
        while new in self._skips:
            if offset < 0:
                offset = 1 - offset
            else:
                offset = - 1 - offset
            new += offset
            # We iterate over multiple arrays and can not be sure the last
            # one of each is bad
            if new <= self._good or (new >= self._bad and
                                     new != (len(self._values) - 1)):
                self.reset(self._last_good, self._last_good)
                return None
        self.current = new
        return self.current

    def steps_left(self):
        """Report the approximate number of remaining steps"""
        variants = self.variants_left()
        if variants > 1:
            return math.ceil((math.log2(variants + 1)))
        return 0

    def variants_left(self):
        """Report the number of variants"""
        if self._bad is None:
            return len(self._values)
        return self._bad - self._good - len(self._skips)

    def reset(self, good=None, bad=None):
        """Reset the bisection, optionally select good/bad positions"""
        self._good = 0 if good is None else good
        self._bad = (len(self._values) - 1) if bad is None else bad
        self._skips = []
        self._update_current()


class Bisections:
    """
    Keeps track of a bisection over multiple arrays
    """

    def __init__(self, args):
        self.args = [Bisection(arg) for arg in args]
        if args:
            self.args[0].reset()
        self._log = []
        self._active = 0

    def current(self):
        """Reports the current variant indexes"""
        return [arg.current for arg in self.args]

    def value(self, variant=None):
        """Reports parameters of the current variant"""
        if variant is None:
            variant = self.current()
        return [self.args[i].value(index)
                for i, index in enumerate(variant)]

    def good(self):
        """Mark the current step as good (go to right)"""
        current = self.current()
        self._log.append(BisectionLogEntry(BisectionStatus.GOOD, current))
        if self._active >= len(self.args):
            return None
        this = self.args[self._active].good()
        if this is None or this == 0:
            self._active += 1
            if self._active >= len(self.args):
                return None
            self.args[self._active].reset()
        return self.current()

    def bad(self):
        """Mark the current step as bad (go to left)"""
        self._log.append(BisectionLogEntry(BisectionStatus.BAD,
                                           self.current()))
        if self._active >= len(self.args):
            return None
        #_this = self.args[self._active].current
        this = self.args[self._active].bad()
        if this is None:  # or this == 0:
            self._active += 1
            if self._active >= len(self.args):
                return None
            self.args[self._active].reset()
        return self.current()

    def skip(self):
        """Mark the current step as skip (untestable)"""
        self._log.append(BisectionLogEntry(BisectionStatus.SKIP,
                                           self.current()))
        if self._active >= len(self.args):
            return None
        this = self.args[self._active].skip()
        if this is None:  # or this == 0:
            self._active += 1
            if self._active >= len(self.args):
                return None
            self.args[self._active].reset()
        return self.current()

    def steps_left(self):
        """Report how many steps to test"""
        return sum(_.steps_left() for _ in self.args)

    def variants_left(self):
        """Report how many variants to test"""
        return sum(_.variants_left() for _ in self.args)

    def log(self):
        """Report bisection log"""
        return('\n'.join(str(entry) for entry in self._log))


class Bisecter:

    """Cmdline app to drive bisection"""

    args = None
    bisection = None

    def __call__(self, command_line=None):
        """
        Perform the execution
        """
        self.args = self.parse_args(command_line)
        func = {'start': self.start,
                'good': self.status,
                'bad': self.status,
                'skip': self.status,
                'run': self.run,
                'args': self.arguments,
                'id': self.identifier,
                'log': self.log,
                'reset': self.reset}.get(self.args.cmd)
        if func is None:
            sys.stderr.write("Unknown command {self.args.cmd}\n")
            sys.exit(-1)
        return func()

    def parse_args(self, command_line=None):
        """
        Define arguments
        """
        def variant_id(arg):
            """Parse variant ID"""
            return [int(_) for _ in arg.split('-')]
        parser = argparse.ArgumentParser(prog='Bisecter', description='Allows '
                                         'to bisect over arbitrary number of '
                                         'arguments.')
        parser.add_argument('--state-file', help='Override path to the '
                            'bisection metadata file (%(default)s)',
                            default='./.bisecter_state',
                            type=os.path.abspath)
        subparsers = parser.add_subparsers(dest='cmd')
        start = subparsers.add_parser('start', help='Initialize bisection')
        start.add_argument('--from-file', help='Read arguments from YAML file')
        start.add_argument('--extended-arguments', '-E', help='On top of the '
                           'comma separated arguments allow certain evals, '
                           'eg. foo,range(10,31,10),bar becomes ["foo", "10", '
                           '"20", "30", "bar"]', action='store_true')
        start.add_argument('arguments', help='Specify one or multiple comma '
                           'separated lists of values this bisection will '
                           'iterate over; bisecter assumes '
                           'the first item of each argument as good and the '
                           'last item as bad.', nargs='+')
        for status in ("good", "bad", "skip"):
            _ = subparsers.add_parser(status, help='Tag the current '
                                      f'result as {status}; get the '
                                      'next arguments by running '
                                      '"bisecter args"')
        run = subparsers.add_parser('run', help='Run your script, appending '
                                    'combinations of the arguments '
                                    'specified in "bisecter start". Exit '
                                    'code 0 means good; 1 - 124 and 126 - 127 '
                                    'means bad; 125 means skip; 128 - 255 '
                                    'means interrupt the bisection.')
        run.add_argument('command', help='Command to be executed',
                         nargs=argparse.REMAINDER)
        args = subparsers.add_parser('args', help='Report the variant '
                                     'arguments. To consume them you can use '
                                     '\'your_script "$(bisecter args)"\' (use '
                                     'the " quotation to preserve special '
                                     'characters).')
        args.add_argument('id', help='Id of the variant which arguments you '
                          'are interested in (current)', nargs='?',
                          type=variant_id)
        args.add_argument('--raw', '-r', help="Report raw arguments in "
                          "python format", action='store_true')
        _ = subparsers.add_parser('id', help='Report the current variant'
                                  ' identifier that can serve to link '
                                  'log entries to arguments')
        _ = subparsers.add_parser('log', help='Report the bisection log')
        _ = subparsers.add_parser('reset', help='Cleanup the bisection '
                                  'by removing all associated files.')
        return parser.parse_args(command_line)

    def _save_state(self):
        """
        Records the self.bisection in a state file
        """
        try:
            with open(self.args.state_file, 'bw') as fd_state:
                pickle.dump(self.bisection, fd_state)
        except pickle.UnpicklingError as details:
            sys.stderr.write("Failed to write bisecter state to "
                             f"{self.args.state_file}: {details}\n")
            sys.exit(-1)
        except IOError as details:
            sys.stderr.write("Failed to open bisecter state file "
                             f"{self.args.state_file}: {details}\n")
            sys.exit(-1)

    def _load_state(self):
        """
        Reads the state file and updates self.bisection
        """
        try:
            with open(self.args.state_file, 'br') as fd_state:
                self.bisection = pickle.load(fd_state)
        except pickle.UnpicklingError as details:
            sys.stderr.write("Failed to read bisecter state from "
                             f"{self.args.state_file}: {details}\n")
            sys.exit(-1)
        except IOError as details:
            sys.stderr.write("Failed to open bisecter state file "
                             f"{self.args.state_file}, please run "
                             f"'{sys.argv[0]} start' first ({details})\n")
            sys.exit(-1)

    def _parse_extended_args(self, arguments):
        def range_repl(matchobj):
            args = []
            if '.' in matchobj.group(2):
                args.append(float(matchobj.group(2)))
            else:
                args.append(int(matchobj.group(2)))
            for arg in matchobj.groups()[2:]:
                if arg is None:
                    continue
                if '.' in arg:
                    args.append(float(arg[1:]))
                else:
                    args.append(int(arg[1:]))
            return ','.join(str(_) for _ in range(*args))

        re_range = re.compile(r'(range\(([^\),]+)(,[^\),]+)?(,[^\),]+)?\))')
        args = []
        for arg in arguments:
            line = re_range.sub(range_repl, arg)
            args.append(self._split_by_comma(line))
        return args

    @staticmethod
    def _split_by_comma(arg):
        return [val.replace('\\,', ',') for val in re.split(r'(?<!\\),', arg)]

    def start(self):
        """
        Initialize the work dirs and define arguments
        """
        if self.args.from_file:
            if self.args.arguments:
                sys.stderr.write('WARNING: Replacing arguments specified '
                                 'as positional arguments with the ones '
                                 f'from "{self.args.from_file}" file\n')
            try:
                import yaml     # optional dependency pylint: disable=C0415
            except ImportError:
                sys.stderr.write("PyYAML not installed, unable to load "
                                 "arguments from file\n")
                sys.exit(-1)
            try:
                with open(self.args.from_file, encoding='utf8') as inp:
                    arguments = yaml.load(inp, yaml.SafeLoader)
            except yaml.YAMLError as details:
                sys.stderr.write('Failed to load arguments from '
                                 f'{self.args.from_file}: {details}\n')
                sys.exit(-1)
            except IOError as details:
                sys.stderr.write('Failed to read arguments file '
                                 f'{self.args.from_file}: {details}\n')
                sys.exit(-1)
        elif self.args.extended_arguments:
            arguments = self._parse_extended_args(self.args.arguments)
        else:
            arguments = []
            for arg in self.args.arguments:
                arguments.append(self._split_by_comma(arg))
        self.bisection = Bisections(arguments)
        if os.path.exists(self.args.state_file):
            sys.stderr.write(f"Bisection in '{self.args.state_file}' already "
                             "in progress\n")
            sys.exit(-1)
        self._save_state()
        self._value()

    def _value(self, variant=None):
        """
        Report value of the current variant in a simple form
        """
        print(' '.join(pipes.quote(_) for _ in self.bisection.value(variant)))

    def _report_remaining_steps(self):
        """
        Report remaining steps count
        """
        sys.stderr.write(f"Bisecting: {self.bisection.variants_left()} variants "
                         " left to test after this (roughly "
                         f"{self.bisection.steps_left()} steps)\n")

    def status(self):
        """
        Set the result of the current bisection combination
        """
        self._load_state()
        ret = getattr(self.bisection, self.args.cmd)()
        self._save_state()
        if ret is None:
            # TODO: Add clever messages about first/last arguments...
            print("Bisection complete, last good combination is "
                  f"{self._value()}")
            return
        self._report_remaining_steps()
        self._value()

    def run(self):
        """
        Keep executing args.command using it's exit code to drive the bisection
        """
        self._load_state()
        with open(os.devnull, "r+", encoding="utf-8") as devnull:
            bret = True
            while bret is not None:
                self._save_state()
                self._report_remaining_steps()
                args = self.args.command + self.bisection.value()
                sys.stderr.write(f"Running {args}\n")
                ret = subprocess.run(args, stdin=devnull, check=False)
                if ret.returncode == 0:
                    bret = self.bisection.good()
                elif ret.returncode == 125:
                    bret = self.bisection.skip()
                elif ret.returncode <= 127:
                    bret = self.bisection.bad()
                else:
                    sys.stderr.write(f"Command {' '.join(self.args.command)}"
                                     f"returned {ret.returncode}, interrupting"
                                     " the automated bisection.")
                    sys.exit(-1)
        self._value()

    def arguments(self):
        """
        Print arguments of the bisection variant
        """
        self._load_state()
        if self.args.id:
            variant = self.args.id
        else:
            variant = None
        if self.args.raw:
            print(self.bisection.value(variant))
        else:
            self._value(variant)

    def identifier(self):
        """
        Print identifier of the current variant as shown by log
        """
        self._load_state()
        print('-'.join(str(_) for _ in self.bisection.current()))

    def log(self):
        """
        Print bisection log
        """
        self._load_state()
        print(self.bisection.log())
        if self.bisection.variants_left() == 0:
            print("Bisection complete, last good combination:")
            self._value()

    def reset(self):
        """
        Remove associated files
        """
        if not os.path.exists(self.args.state_file):
            sys.stderr.write(f"No bisection in '{self.args.state_file}' "
                             "in progress\n")
        else:
            try:
                os.remove(self.args.state_file)
            except IOError as details:
                sys.stderr.write(f"Failed to remove '{self.args.state_file}': "
                                 f"{details}\n")
                sys.exit(-1)

if __name__ == '__main__':
    APP = Bisecter()
    sys.exit(APP())
