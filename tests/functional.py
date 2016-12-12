from __future__ import unicode_literals

import functools
import logging
import os
import re
from rpaths import Path
import subprocess
import sys
import time

from tej.submission import make_unique_name
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
        print("\ntej-tests$ " +
              " ".join(a if isinstance(a, unicode_)
                       else a.decode('utf-8', 'replace')
                       for a in args))
        return f(args, **kwargs)
    return wrapper


@print_arg_list
def call(args, cwd=None):
    return subprocess.call(args, cwd=cwd)


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

    if 'COVER' in os.environ:
        tej = os.environ['COVER'].split(' ') + [
            bytes(Path.cwd() / 'tej/__main__.py'),
            '-v', '-v']
    else:
        tej = ['tej', '-v', '-v']

    for path in ('~/.tej', '~/tej 2'):
        path = Path(path).expand_user()
        try:
            path.remove()
        except OSError:
            path.rmtree(ignore_errors=True)
    Path('~/tej 2').expand_user().mkdir()

    logging.info("Creating default queue")
    check_call(tej + ['setup', destination])
    assert Path('~/.tej').expand_user().is_dir()
    Path('~/.tej').expand_user().rmtree()

    logging.info("Creating a queue with a link")
    check_call(tej + ['setup', destination,
                      '--queue', 'tej 2/queue',
                      '--make-link', 'tej 2/link'])
    assert Path('~/tej 2/queue').expand_user().is_dir()
    with Path('~/tej 2/link').expand_user().open('r') as fp:
        assert fp.read() == ('tejdir: %s\n' %
                             Path('~/tej 2/queue').expand_user())

    logging.info("Adding links")
    check_call(tej + ['setup', destination, '--only-links',
                      '--queue', '~/tej 2/queue',
                      '--make-link', '~/tej 2/link2'])
    with Path('~/tej 2/link2').expand_user().open('r') as fp:
        assert fp.read() == ('tejdir: %s\n' %
                             Path('~/tej 2/queue').expand_user())
    assert not Path('~/.tej').expand_user().exists()
    check_call(tej + ['setup', destination, '--only-links',
                      '--queue', '~/tej 2/queue',
                      '--make-default-link'])
    with Path('~/.tej').expand_user().open('r') as fp:
        assert fp.read() == ('tejdir: %s\n' %
                             Path('~/tej 2/queue').expand_user())

    logging.info("Calling status for non-existent job")
    output = check_output(tej + ['status', destination, '--id', 'nonexistent'])
    assert output == b'not found\n'

    logging.info("Submitting a job")
    jobdir = Path.tempdir(prefix='tej-tests-')
    try:
        with jobdir.open('w', 'start.sh', newline='\n') as fp:
            fp.write('#!/bin/sh\n'
                     '[ -f dir1/data1 ] || exit 1\n'
                     '[ "$(cat dir2/dir3/data2)" = data2 ] || exit 2\n'
                     'echo "stdout here"\n'
                     'while ! [ -e ~/"tej 2/job1done" ]; do\n'
                     '    sleep 1\n'
                     'done\n'
                     'echo "job output" > job1results\n')
        with jobdir.mkdir('dir1').open('wb', 'data1') as fp:
            fp.write(b'data1\n')
        with jobdir.mkdir('dir2').mkdir('dir3').open('w', 'data2') as fp:
            fp.write('data2\n')
        job_id = check_output(tej + ['submit', destination, jobdir.path])
        job_id = job_id.rstrip().decode('ascii')
    finally:
        jobdir.rmtree()

    logging.info("Check status while forgetting job id")
    assert call(tej + ['status', destination]) != 0

    logging.info("Check status of running job")
    output = check_output(tej + ['status', destination, '--id', job_id])
    assert output == b'running\n'

    logging.info("Finish job")
    Path('~/tej 2/job1done').expand_user().open('w').close()
    time.sleep(2)

    logging.info("Check status of finished job")
    output = check_output(tej + ['status', destination, '--id', job_id])
    assert output == b'finished 0\n'

    logging.info("Download job results")
    destdir = Path.tempdir(prefix='tej-tests-')
    try:
        check_call(tej + ['download', destination, '--id', job_id,
                          'job1results', '_stdout'],
                   cwd=destdir.path)
        with destdir.open('r', 'job1results') as fp:
            assert fp.read() == 'job output\n'
        with destdir.open('r', '_stdout') as fp:
            assert fp.read() == 'stdout here\n'
    finally:
        destdir.rmtree()

    logging.info("List jobs")
    output = check_output(tej + ['list', destination])
    assert output == ('%s finished\n' % job_id).encode('ascii')

    logging.info("Kill already finished job")
    output = check_output(tej + ['kill', destination, '--id', job_id])
    assert output == b''

    logging.info("Remove finished job")
    check_call(tej + ['delete', destination, '--id', job_id])
    output = check_output(tej + ['status', destination, '--id', job_id])
    assert output == b'not found\n'

    logging.info("Submit another job")
    jobdir = Path.tempdir(prefix='tej-tests-')
    try:
        with jobdir.open('w', 'start.sh', newline='\n') as fp:
            fp.write('#!/bin/sh\n'
                     'sleep 20\n')
        job_id = make_unique_name()
        check_call(tej + ['submit', destination, '--id', job_id, jobdir.path])
    finally:
        jobdir.rmtree()
    output = check_output(tej + ['status', destination, '--id', job_id])
    assert output == b'running\n'

    logging.info("Remove still running job")
    assert call(tej + ['delete', destination, '--id', job_id]) != 0

    logging.info("Kill running job")
    output = check_output(tej + ['kill', destination, '--id', job_id])
    output = check_output(tej + ['status', destination, '--id', job_id])
    assert re.match(b'finished [0-9]+\n', output)

    logging.info("Remove killed job")
    check_call(tej + ['delete', destination, '--id', job_id])
    output = check_output(tej + ['status', destination, '--id', job_id])
    assert output == b'not found\n'

    jobdir = Path.tempdir(prefix='tej-tests-')
    try:
        logging.info("Start remote command job")
        job_id = check_output(tej + ['submit', destination,
                                     '--script', 'echo "hi"', jobdir.path])
        job_id = job_id.rstrip().decode('ascii')
    finally:
        jobdir.rmtree()
    time.sleep(2)

    logging.info("Download remote command job output")
    destdir = Path.tempdir(prefix='tej-tests-')
    try:
        check_call(tej + ['download', destination, '--id', job_id, '_stdout'],
                   cwd=destdir.path)
        with destdir.open('r', '_stdout') as fp:
            assert fp.read() == 'hi\n'
    finally:
        destdir.rmtree()

    logging.info("Remove finished job")
    output = check_output(tej + ['delete', destination, '--id', job_id])
    assert output == b''
    output = check_output(tej + ['status', destination, '--id', job_id])
    assert output == b'not found\n'
