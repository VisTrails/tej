import functools
import logging
import os
from rpaths import Path
import subprocess

from tej.utils import unicode_


def print_arg_list(f):
    """Decorator printing the sole argument (list of strings) first.
    """
    @functools.wraps(f)
    def wrapper(args):
        print("tej-tests$ " +
              " ".join(a if isinstance(a, unicode_)
                       else a.decode('utf-8', 'replace')
                       for a in args))
        return f(args)
    return wrapper


@print_arg_list
def check_call(args):
    return subprocess.check_call(args)


def functional_tests():
    destination = os.environ['TEJ_DESTINATION']
    logging.info("Using TEJ_DESTINATION %s" % destination)

    logging.info("Creating default queue")
    check_call(['tej', 'setup', destination])
    assert Path('~/.tej').expand_user().is_dir()
