from rpaths import Path
import subprocess
import unittest


class TestTimeDelta(unittest.TestCase):
    def call_function(self, delta):
        p = subprocess.Popen(
            ['/bin/sh', '-s', '%d' % delta],
            cwd=(Path(__file__).parent.parent /
                 'tej/remotes/default/commands').path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE)
        stdout, stderr = p.communicate(b"""
#!/bin/sh
set -e
. "lib/utils.sh"
format_timedelta "$1"
""")
        self.assertEqual(p.wait(), 0)
        return stdout

    def test_format(self):
        self.assertEqual(self.call_function(0),
                         b'0:00\n')
        self.assertEqual(self.call_function(4),
                         b'0:04\n')
        self.assertEqual(self.call_function(42),
                         b'0:42\n')

        self.assertEqual(self.call_function(120),
                         b'2:00\n')
        self.assertEqual(self.call_function(124),
                         b'2:04\n')
        self.assertEqual(self.call_function(154),
                         b'2:34\n')

        self.assertEqual(self.call_function(3599),
                         b'59:59\n')
        self.assertEqual(self.call_function(3600),
                         b'1:00:00\n')
        self.assertEqual(self.call_function(3602),
                         b'1:00:02\n')
        self.assertEqual(self.call_function(3660),
                         b'1:01:00\n')
        self.assertEqual(self.call_function(5400),
                         b'1:30:00\n')
        self.assertEqual(self.call_function(3722),
                         b'1:02:02\n')
        self.assertEqual(self.call_function(3762),
                         b'1:02:42\n')
        self.assertEqual(self.call_function(9762),
                         b'2:42:42\n')
        self.assertEqual(self.call_function(25200),
                         b'7:00:00\n')
