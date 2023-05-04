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

import bisecter
import os
from unittest import mock
import unittest
import json

from bisecter import utils


class Utils(unittest.TestCase):

    def test_simple_template(self):
        strings = ['something', '{1}', 'foo{2}', 'bar{{3}}', 'baz{{3}',
                   'buz{3}}', "FOO{3}}A", "{0}{1}.{2}}--{{-1}"]
        values = ["A", "B", "C", "D"]
        self.assertEqual(["something", "B", "fooC", "bar{3}", "baz{D",
                          "buzD}", "FOOD}A", "AB.C}--{D"],
                          utils.simple_template(strings, values))
        self.assertRaises(utils.ReplaceIndexError, utils.simple_template,
                          ["{4}"], [0, 1, 2, 3])

    def test_range_beaker(self):
        # Check it won't fail (ignore bkr call/limit for now)
        with open(os.path.join(os.path.dirname(__file__), 'assets',
                  'bkr.json'), 'rb') as fd_bkr:
            ret = mock.Mock()
            ret.stdout = fd_bkr.read()
            bkr = mock.Mock()
            bkr.return_value = ret
        distros = ['Distro-1.2.0-20230110', 'Distro-1.2.0-20230109',
                   'Distro-1.2.0-20230108', 'Distro-1.2.0-20230107',
                   'Distro-1.2.0-20230106', 'Distro-1.2.0-20230105',
                   'Distro-1.2.0-20230104']
        with mock.patch('bisecter.subprocess.run', bkr):
            self.assertEqual(distros,
                             bisecter.range_beaker("beaker://Distro-"))
            self.assertEqual(distros[:-2], bisecter.range_beaker(
                "beaker://Distro-1.2:Distro-1.2.0-20230106"))
            self.assertEqual(distros, bisecter.range_beaker(
                "beaker://Distro-1.2:-3"))
            self.assertEqual(distros[3:-1], bisecter.range_beaker(
                "beaker://Distro-1.2.0-20230107:Distro-1.2.0-20230105:7"))

    def test_range_url(self):
        self.maxDiff = None
        with open(os.path.join(os.path.dirname(__file__), 'assets',
                  'koji-kernel.html'), 'rb') as fd_html:
            req = mock.Mock()
            req.read.return_value = fd_html.read()
            urlopen = mock.MagicMock()
            urlopen.return_value.__enter__.return_value = req
        with open(os.path.join(os.path.dirname(__file__), 'assets',
                  'koji-kernel-links.json'), 'r', encoding='utf-8') as fd_urls:
            urls = json.load(fd_urls)
        with mock.patch('bisecter.urllib.request.urlopen', urlopen):
            self.assertEqual(135, len(bisecter.range_url(
                'url://https\\://koji.fedoraproject.org/koji//packageinfo?'
                'packageID=8')))
            self.assertEqual(urls, bisecter.range_url(
                'url://https\\://koji.fedoraproject.org/koji//packageinfo?'
                'packageID=8:kernel-\\d'))
            self.assertEqual(urls[4:], bisecter.range_url(
                'url://https\\://koji.fedoraproject.org/koji//packageinfo?'
                'packageID=8:kernel-\\d:+4'))
            self.assertEqual(urls[-4:], bisecter.range_url(
                'url://https\\://koji.fedoraproject.org/koji//packageinfo?'
                'packageID=8:kernel-\\d:-4'))
            self.assertEqual(urls[-8:4], bisecter.range_url(
                'url://https\\://koji.fedoraproject.org/koji//packageinfo?'
                'packageID=8:kernel-\\d:-8:+4'))
            self.assertEqual(urls[-8:-2], bisecter.range_url(
                'url://https\\://koji.fedoraproject.org/koji//packageinfo?'
                'packageID=8:kernel-\\d:-8:-2'))
            self.assertEqual(urls[3:6], bisecter.range_url(
                'url://https\\://koji.fedoraproject.org/koji//packageinfo?'
                'packageID=8:kernel-\\d:kernel-6.1.14-100.*:'
                'kernel-6.1.14-200.*'))
            self.assertEqual(urls[3:6], bisecter.range_url(
                'url://https\\://koji.fedoraproject.org/koji//packageinfo?'
                'packageID=8:kernel-\\d:kernel-6.1.14-100.*:+6'))


if __name__ == '__main__':
    unittest.main()
