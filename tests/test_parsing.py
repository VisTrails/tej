from __future__ import unicode_literals

import getpass
import unittest

import tej.submission
from tej.submission import InvalidDestination
from tej.utils import irange, unicode_


class TestUtils(unittest.TestCase):
    def test_unique_names(self):
        names = [tej.submission.make_unique_name() for i in irange(5)]
        self.assertEqual(len(set(names)), 5)
        self.assertTrue(all(isinstance(n, unicode_) and len(n) == 10
                            for n in names))

    def test_shell_escape(self):
        shell_escape = tej.submission.shell_escape
        self.assertEqual(shell_escape("test"), "test")
        self.assertEqual(shell_escape("hello world"), '"hello world"')
        self.assertEqual(shell_escape('some"thing'), '"some\\"thing"')


class TestDestination(unittest.TestCase):
    def test_parse(self):
        parse = tej.submission.parse_ssh_destination
        user = getpass.getuser()
        self.assertEqual(parse('127.0.0.1'), {'hostname': '127.0.0.1',
                                              'username': user})
        self.assertEqual(parse('ssh://127.0.0.1'), {'hostname': '127.0.0.1',
                                                    'username': user})
        self.assertEqual(parse('127.0.0.1:12'), {'hostname': '127.0.0.1',
                                                 'username': user,
                                                 'port': 12})
        self.assertEqual(parse('ssh://127.0.0.1:12'), {'hostname': '127.0.0.1',
                                                       'username': user,
                                                       'port': 12})
        self.assertEqual(parse('me@host:12'), {'hostname': 'host',
                                               'username': 'me',
                                               'port': 12})
        self.assertEqual(parse('me:p4$$w0rd@host:12'), {'hostname': 'host',
                                                        'username': 'me',
                                                        'password': 'p4$$w0rd',
                                                        'port': 12})
        self.assertEqual(parse('ssh://me@host:12'), {'hostname': 'host',
                                                     'username': 'me',
                                                     'port': 12})
        self.assertEqual(parse('ssh://me:p@host:12'), {'hostname': 'host',
                                                       'username': 'me',
                                                       'password': 'p',
                                                       'port': 12})
        self.assertEqual(parse('ssh://me@host:22'), {'hostname': 'host',
                                                     'username': 'me',
                                                     'port': 22})
        self.assertRaises(InvalidDestination, parse, 'http://host')
        self.assertRaises(InvalidDestination, parse, 'ssh://test@test@host')
        self.assertRaises(InvalidDestination, parse, 'ssh://host:port')

    def test_string(self):
        string = tej.submission.destination_as_string
        self.assertEqual(string({'hostname': '127.0.0.1', 'port': 12,
                                 'username': 'somebody'}),
                         'ssh://somebody@127.0.0.1:12')
        self.assertEqual(string({'hostname': '127.0.0.1', 'port': 12,
                                 'username': 'somebody', 'password': '$$'}),
                         'ssh://somebody:$$@127.0.0.1:12')
        self.assertEqual(string({'hostname': '127.0.0.1', 'port': 22,
                                 'username': 'somebody'}),
                         'ssh://somebody@127.0.0.1')
        self.assertEqual(string({'hostname': '127.0.0.1', 'port': 22,
                                 'username': 'somebody', 'password': 'pass'}),
                         'ssh://somebody:pass@127.0.0.1')
        self.assertEqual(string({'hostname': '127.0.0.1',
                                 'username': 'somebody'}),
                         'ssh://somebody@127.0.0.1')
