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

bisector start '["some", "values"]' '["another", "values"]'
my_script "$(bisector args)" $(bisector id)
bisector good
my_script "$(bisector args)" $(bisector id)
bisector bad
...
bisector log
bisector reset

bisector start '["some", "values"]' '["another", "values"]'
bisector run my_script
bisector log
bisector reset
"""

import argparse
import enum
import os
import sys

import yaml


class BisectionStatus(enum.Enum):
    GOOD = 0
    BAD = 1
    SKIP = 125


class BisectionLogEntry:
    def __init__(self, status, identifier):
        self.status = status
        self.identifier = identifier


class Bisections:
    """
    Keeps track of the bisection statuses
    """
    def __init__(self, args):
        print("INIT")
        self.args = [Bisection(arg) for arg in args]
        self._log = []
        self.last_good = [0] * len(self.args)
        self._active = 0
        
    def current(self):
        return [arg.middle if i == self._active else self.last_good[i]
                for i, arg in enumerate(self.args)]
        
    def value(self):
        return [self.args[i] for i in self.current()]
    
    def good(self):
        self._check_duplicities()
        #input(f"GOOD {self.current()} ({self._active}) ({self.args[self._active]._good} {self.args[self._active].middle} {self.args[self._active]._bad})")
        print(f"GOOD {self.current()} ({self._active}) ({self.args[self._active]._good} {self.args[self._active].middle} {self.args[self._active]._bad})")
        self.last_good = current = self.current()
        self._log.append(BisectionLogEntry(BisectionStatus.GOOD, current))
        this = self.args[self._active].good()
        if this is None or this == 0:
            self._active += 1
            if self._active >= len(self.args):
                return None
        return self.current()
    
    def bad(self):
        self._check_duplicities()
        _this = self.args[self._active].middle
        #input(f"BAD {self.current()} ({self._active}) ({self.args[self._active]._good} {self.args[self._active].middle} {self.args[self._active]._bad})")
        print(f"BAD {self.current()} ({self._active}) ({self.args[self._active]._good} {self.args[self._active].middle} {self.args[self._active]._bad})")
        self._log.append(BisectionLogEntry(BisectionStatus.BAD,
                                           self.current()))
        this = self.args[self._active].bad()
        if this is None or this == 0:
            self.last_good[self._active] = _this - 1
            self._active += 1
            if self._active >= len(self.args):
                return None
        return self.current()

    def _check_duplicities(self):
        # TODO: Remove this, just for internal testing
        a = set("-".join(str(ident) for ident in _.identifier) for _ in self._log)
        if len(a) != len(self._log):
            raise Exception("Variant tested multiple times!")

    def log(self):
        return('\n'.join(f"{entry.status.name:4s} {entry.identifier}"
                         for entry in self._log))

class Bisection:
    """
    Keeps track of the current bisection
    """
    def __init__(self, values):
        self._values = values
        self.reset()
        
    @property
    def value(self):
        return self._values[self.middle]
    
    def _update_current(self):
        self.middle = (self._good + self._bad) // 2
        
    def good(self):
        self._good = self.middle + 1
        if self._good >= self._bad:
            return None
        self._update_current()
        return self.middle
    
    def bad(self):
        self._bad = self.middle
        if self._bad <= self._good:
            return None
        self._update_current()
        return self.middle
    
    def reset(self, good=None, bad=None):
        self._good = 0 if good is None else good
        self._bad = len(self._values) if bad is None else bad
        self._update_current()


def parse_args(command_line=None):
    """
    Define arguments
    """
    parser = argparse.ArgumentParser(prog='Bisector', description='Allows'
                                     'to bisect over arbitrary number of '
                                     'arguments.')
    parser.add_argument('--work-dir', help='Which directory to store '
                        'metadata in. (%(default)s)', default='.')
    subparsers = parser.add_subparsers(dest='command')
    start = subparsers.add_parser('start', help='Initialize bisection')
    start.add_argument('--from-file', help='Read arguments from YAML file')
    start.add_argument('arguments', help='Python-like iterable arguments, '
                       'eg. \'[1, 5, 8]\' \'["one", "two", "three"]\' '
                       '\'list(range(10)) + [-7]\' ...; bisector assumes '
                       'the first variant (1 one 0) is good and the last '
                       '(8 three -7) is bad.', nargs='+')
    for status in ("good", "bad", "skip"):
        subparser = subparsers.add_parser(status, help='Tag the current '
                                          f'result as {status}; get the '
                                          'next arguments by running '
                                          '"bisector args"')
    run = subparsers.add_parser('run', help='Run your script, appending '
                                'combinations of the arguments '
                                'specified in "bisector start". Exit '
                                'code 0 means good; 1 - 124 and 126 - 127 '
                                'means bad; 125 means skip; 128 - 255 means '
                                'interrupt the bisection.')
    run.add_argument('command', 'Command to be executed',
                     nargs=argparse.REMAINDER)
    args = subparsers.add_parser('args', help='Report the variant '
                                 'arguments. To consume them you can use '
                                 '\'your_script "$(bisector args)"\' (use '
                                 'the " quotation to preserve special '
                                 'characters).')
    args.add_argument('id', help='Id of the variant which arguments you are '
                      'interested in (current)', nargs='?')
    identifier = subparsers.add_parser('id', help='Report the current variant'
                                       ' identifier that can serve to link '
                                       'log entries to arguments')
    log = subparsers.add_parser('log', help='Report the bisection log')
    reset = subparsers.add_parser('reset', help='Cleanup the bisection '
                                  'by removing all associated files.')
    return parser.parse_args(command_line)


def _read_workdir(workdir):
    """
    Read workdir and return current and arguments

    :param workdir: Path to the workdir
    :returns: current, arguments
    """
    base = os.path.join(workdir, '.bisector_workdir')
    try:
        with open(os.path.join(base, 'args.yml'), encoding='utf8') as inp:
            arguments = yaml.load(inp, yaml.SafeLoader)
        with open(os.path.join(base, 'current.yml'), encoding='utf8') as inp:
            current = yaml.load(inp, yaml.SafeLoader)
    except IOError as details:
        sys.stderr.write(f"Failed to read {workdir} workdir: {details}")
        sys.exit(1)
    return current, arguments

def start(args):
    """
    Initialize the work dirs and define arguments
    """
    path = os.path.join(args.work_dir, '.bisector_workdir')
    if os.path.exists(path):
        sys.stderr.write(f"Bisection in '{path}' already in progress\n")
        sys.exit(1)
    try:
        os.makedirs(path)
    except IOError as details:
        sys.stderr.write(f"Failed to create '{path}' workdir: {details}\n")
        sys.exit(1)

    with open(os.path.join(path, 'args.yml'), 'w', encoding='utf8') as out:
        if args.from_file:
            if args.arguments:
                sys.stderr.write('WARNING: Replacing arguments specified '
                                 'as positional arguments with the ones '
                                 f'from "{args.from_file}" file')
            with open(args.from_file, encoding='utf8') as inp:
                arguments = yaml.load(inp, yaml.SafeLoader)
        else:
            arguments = args.arguments
        output.write(yaml.dump(arguments))

    with open(os.path.join(path, 'current.yml', 'w', encoding='utf8')) as out:
        current = [len(arg) // 2 for arg in arguments]
        out.write(yaml.dump(current))


def status(args):
    """
    Perform the jump between variants according to the status
    """
    current, args = _read_workdir(args.work_dir)
    # TODO


def main():
    """
    Perform the execution
    """
    args = parse_args()
    func = {'start': start,
            'good': status,
            'bad': status,
            'skip': status,
            'run': run,
            'args': arguments,
            'id': identifier,
            'log': log,
            'reset': reset}.get(args.command)
    if func is None:
        raise NotImplementedError(f"Unknown subparser {args.command}")
    return func(args)


if __name__ == '__main__':
    sys.exit(main(args))
