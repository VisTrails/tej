from __future__ import unicode_literals

import functools
import logging
import os
from rpaths import Path
import subprocess
import sys
import time

from tej.utils import unicode_


if hasattr(sys.stdout, 'buffer') and hasattr(sys.stdout.buffer, 'write'):
    stdout_bytes = sys.stderr.buffer
else:
    stdout_bytes = sys.stderr


def print_arg_list(f):
    """Decorator printing the sole argument (list of strings) first.
    """
    @functools.wraps(f)
    def wrapper(args, **kwargs):
        print("tej-tests$ " +
              " ".join(a if isinstance(a, unicode_)
                       else a.decode('utf-8', 'replace')
                       for a in args))
        return f(args, **kwargs)
    return wrapper


@print_arg_list
def check_call(args, cwd=None):
    return subprocess.check_call(args, cwd=cwd)


@print_arg_list
def check_output(args, cwd=None):
    output = subprocess.check_output(args, cwd=cwd)
    stdout_bytes.write(output)
    return output


def functional_tests():
    destination = os.environ['TEJ_DESTINATION']
    logging.info("Using TEJ_DESTINATION %s" % destination)

    for path in ('~/.tej', '~/tej2'):
        path = Path(path).expand_user()
        try:
            path.remove()
        except OSError:
            path.rmtree(ignore_errors=True)
    Path('~/tej2').expand_user().mkdir()

    logging.info("Creating default queue")
    check_call(['tej', 'setup', destination])
    assert Path('~/.tej').expand_user().is_dir()
    Path('~/.tej').expand_user().rmtree()

    logging.info("Creating a queue with a link")
    check_call(['tej', 'setup', destination,
                '--queue', '~/tej2/queue',
                '--make-link', '~/tej2/link'])
    assert Path('~/tej2/queue').expand_user().is_dir()
    with Path('~/tej2/link').expand_user().open('r') as fp:
        assert fp.read() == 'tejdir: %s\n' % Path('~/tej2/queue').expand_user()

    logging.info("Adding links")
    check_call(['tej', 'setup', destination, '--only-links',
                '--queue', '~/tej2/queue',
                '--make-link', '~/tej2/link2'])
    with Path('~/tej2/link2').expand_user().open('r') as fp:
        assert fp.read() == 'tejdir: %s\n' % Path('~/tej2/queue').expand_user()
    assert not Path('~/.tej').expand_user().exists()
    check_call(['tej', 'setup', destination, '--only-links',
                '--queue', '~/tej2/queue',
                '--make-default-link'])
    with Path('~/.tej').expand_user().open('r') as fp:
        assert fp.read() == 'tejdir: %s\n' % Path('~/tej2/queue').expand_user()

    logging.info("Calling status for non-existent job")
    output = check_output(['tej', 'status', destination, '--id', 'nonexistent'])
    assert output == b'not found\n'

    logging.info("Submitting a job")
    jobdir = Path.tempdir(prefix='tej-tests-')
    try:
        with jobdir.open('w', 'start.sh', newline='\n') as fp:
            fp.write('#!/bin/sh\n'
                     'while ! [ -e ~/tej2/job1done ]; do\n'
                     '    sleep 1\n'
                     'done\n'
                     'echo "job output" > job1results\n')
        job_id = check_output(['tej', 'submit', destination, jobdir.path])
    finally:
        jobdir.rmtree()

    logging.info("Check status of running job")
    output = check_output(['tej', 'status', destination, '--id', job_id])
    assert output == b'running\n'

    logging.info("Finish job")
    Path('~/tej2/job1done').expand_user().open('w').close()
    time.sleep(2)

    logging.info("Check status of finished job")
    output = check_output(['tej', 'status', destination, '--id', job_id])
    assert output == b'finished\n0\n'

    logging.info("Download job results")
    destdir = Path.tempdir(prefix='tej-tests-')
    try:
        check_call(['tej', 'download', destination, '--id', job_id,
                    'job1results'],
                   cwd=destdir.path)
        with destdir.open('r', 'job1results') as fp:
            assert fp.read() == 'job output\n'
    finally:
        destdir.rmtree()

    logging.info("Remove finished job")
    check_call(['tej', 'delete', destination, '--id', job_id])
    output = check_output(['tej', 'status', destination, '--id', job_id])
    assert output == b'not found\n'
