import argparse
import logging
import os
import sys

try:
    import unittest2 as unittest
    sys.modules['unittest'] = unittest
except ImportError:
    import unittest


top_level = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
start_dir = os.path.join(top_level, 'tests')
if top_level not in sys.path:
    sys.path.insert(0, top_level)

sys.path.append(start_dir)


from tests.functional import functional_tests   # noqa


class Program(unittest.TestProgram):
    def createTests(self):
        if self.testNames is None:
            self.test = self.testLoader.discover(
                start_dir=os.path.dirname(os.path.abspath(__file__)),
                pattern='test_*.py')
        else:
            self.test = self.testLoader.loadTestsFromNames(self.testNames)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format="%(asctime)s TEST-%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="tej tests")
    parser.add_argument('--unittests', action='store_true',
                        dest='unittests', default=None)
    parser.add_argument('--no-unittests', action='store_false',
                        dest='unittests', default=None)
    parser.add_argument('--functests', action='store_true',
                        dest='functests', default=None)
    parser.add_argument('--no-functests', action='store_false',
                        dest='functests', default=None)
    parser.add_argument('arg', nargs=argparse.REMAINDER)
    args = parser.parse_args()

    unittests, functests = (lambda a: ({None: not any(a)}.get(x, x)
                            for x in a))((args.unittests, args.functests))

    successful = True
    if unittests:
        logging.info("Running unit tests")
        if not hasattr(unittest, 'skipIf'):
            logging.info("This testsuite will not work with pre-2.7 "
                         "unittest. If running Python 2.6, you'll need to "
                         "install the 'unittest2' package.")
            sys.exit(1)
        prog = Program(argv=['tests'] + args.arg, exit=False)
        successful = prog.result.wasSuccessful()
    if functests:
        logging.info("Running functional tests")
        functional_tests()

    if not successful:
        sys.exit(1)
