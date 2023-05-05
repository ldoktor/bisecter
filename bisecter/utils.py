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

import itertools
import json
import re
import subprocess
import urllib.parse
import urllib.request


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


def esplit(sep, line, maxsplit=0):
    """Split line by {sep} allowing \\ escapes"""
    return [_.replace(f'\\{sep}', sep)
            for _ in re.split(f'(?<!\\\\){sep}', line, maxsplit)]


def range_beaker(arg, arch="x86_64", extra_args=None):
    """
    Parse argument into list of distros

    :param arg: Query for beaker, eg.:
                * beaker://RHEL-9 (all RHEL-9% distros)
                * beaker://RHEL-9.1:-10 (latest 10 RHEL-9.1%)
                * beaker://RHEL-8.1.0:RHEL-8.2.0 (all revisions between)
                * beaker://RHEL-8.1.0:RHEL-8.2.0:-100 (ditto but max 100)
    :return: List of distros (eg.:
        ['Distro-1.2.0-20230110', 'Distro-1.2.0-20230109'])
    """

    def parse_arg(arg):
        args = esplit(':', arg[9:], 2)
        limit = 100
        if len(args) == 3:
            return args[0], args[1], int(args[2])
        if len(args) == 2:
            if args[1].startswith('-'):
                return args[0], None, int(args[1][1:])
            return args[0], args[1], limit
        if len(args) == 1:
            return args[0], None, limit
        raise ValueError("No distro specified")

    def get_common(first, last):
        """
        Get common part of first and last, adding n/d for nightly/daily builds
        """
        if last:
            common = ''.join(char[0] for char in itertools.takewhile(
                lambda _: _[0] == _[1], zip(first, last)))
            if 'n' in first and 'n' in last:
                return common + '%n%'
            if 'd' in first and 'd' in last:
                return common + '%n%'
            return common + '%'
        if 'n' in first:
            return first + '%n%'
        if 'd' in first:
            return first + '%d%'
        return first + '%'

    def distros_from_bkr_json(distros, first, last):
        idistros = iter(distros)
        out = []
        # Look for first
        for distro in idistros:
            dist = distro.get("distro_name")
            if dist and dist.startswith(first):
                out.append(dist)
                break
        # Add all distros until last
        for distro in idistros:
            if not distro.get("distro_name"):
                continue
            if distro["distro_name"] not in out:
                out.append(distro["distro_name"])
            if last and distro["distro_name"].startswith(last):
                break
        return out

    if extra_args is None:
        extra_args = []
    first, last, limit = parse_arg(arg)
    common = get_common(first, last)
    ret = subprocess.run(["bkr", "distro-trees-list", "--arch", arch, "--name",
                          common, "--limit", str(limit), '--format', 'json']
                          +extra_args, capture_output=True, check=True)
    return distros_from_bkr_json(json.loads(ret.stdout), first, last)


def range_url(arg):
    """
    Parse argument into list of links

    :param arg: Query a page for links (koji, python -m http.server, ...):

        * url://example.org (all links from the page)
        * url://example.org:kernel (links containing kernel)
        * url://example.org:kernel:6.0.7 (ditto but start from 6.0.7)
        * url://example.org:kernel:6.0.7:6.1.9
          (links between 6.0.7 and 6.1.9)
        * url://example.org:kernel:+3 (skip first 3 links)
        * url://example.org:kernel:-3 (skip last 3 links)
        * url://example.org:kernel:+3:-2 (skip first 3 and last 2)
          (links_containing_kernel[3:-2])
        * url://example.org:kernel:+0:+5 (report first 5 links - using +/- is
          mandatory!) (links_containing_kernel[:5])

    :return: list of individual links (eg.:
        ["example.org/foo", "example.org/bar"])
    """

    def parse_arg(arg):
        args = esplit(':', arg[6:], 3)
        if len(args) < 4:
            args += [None, ] * (4 - len(args))
        for i in (2, 3):
            if not args[i]:
                continue
            if args[i].startswith('+'):
                args[i] = int(args[i])
            elif args[i].startswith('-'):
                args[i] = int(args[i])
        return args

    def get_filtered_links(page, filt):
        with urllib.request.urlopen(page) as req:
            content = req.read().decode('utf-8')
        if filt is None:
            filt = ''
        return re.findall(f"href=\"([^\"]+)\"[^>]*>({filt}[^<]*)<", content)

    def apply_ranges(links, first, last):
        if isinstance(first, int):
            offset1 = first
            first = None
        else:
            offset1 = 0
        if isinstance(last, int):
            offset2 = last
            last = None
        else:
            offset2 = None
        ilinks = iter(links[offset1:offset2])
        out = []
        # Look for first
        if first:
            for link in ilinks:
                if link[1] and re.match(first, link[1]):
                    out.append(link[0])
                    break
        # Add all links until last
        for link in ilinks:
            if not link[0]:
                continue
            if link[0] not in out:
                out.append(link[0])
            if last and re.match(last, link[1]):
                break
        return out

    page, filt, first, last = parse_arg(arg)
    links = get_filtered_links(page, filt)
    return [urllib.parse.urljoin(page, link)
            for link in apply_ranges(links, first, last)]
