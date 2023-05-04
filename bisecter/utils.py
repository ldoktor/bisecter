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
"""Utils used in the Bisecter tool"""

import re


class ReplaceIndexError(IndexError):

    """Error replacing value in list"""

    def __init__(self, match, values, strings):
        self.match = match
        self.values = values
        self.strings = strings

    def __str__(self):
        return (f"Incorrect index in '{self.match}' from {self.strings} "
                f"for values {self.values}")


def simple_template(strings, values):
    """
    Simple templating to replace {\\d} occurrences with items in values

    :param strings: List of strings to be replaced
    :param values: Values to be used in teplating
    :return: List of strings with {\\d} entries replaced with provided values
    """

    def do_template(matchobj):
        match_str = matchobj.group(0)
        if match_str.startswith('{{') and match_str.endswith('}}'):
            return match_str[1:-1]
        num = int(matchobj.group(1))
        try:
            replaced = str(values[num])
        except IndexError as exc:
            raise ReplaceIndexError(matchobj, values, strings) from exc
        if match_str.startswith('{{'):
            replaced = '{' + replaced
        elif match_str.endswith('}}'):
            replaced += '}'
        return replaced

    pattern = r'\{?\{(-?\d+)\}\}?'
    return [re.sub(pattern, do_template, item) for item in strings]
