from __future__ import absolute_import, division

from collections import namedtuple

import tej

from vistrails.core.modules.vistrails_module import Module, ModuleError, \
    ModuleSuspended
from vistrails.core.vistrail.job import JobMixin


class Queue(Module):
    """A connection to a queue on a remote server.

    `hostname` can be a hostname or a full destination in the format:
    ``[ssh://][user@]server[:port]``, e.g. ``vistrails@nyu.edu``.
    """
    _input_ports = [('hostname', '(basic:String)'),
                    ('username', '(basic:String)',
                     {'optional': True}),
                    ('port', '(basic:Integer)',
                     {'optional': True, 'defaults': "['22']"}),
                    ('queue', '(basic:String)',
                     {'optional': True, 'defaults': "['~/.tej']"})]
    _output_ports = [('queue', '(org.vistrails.extra.tej:Queue)')]

    def compute(self):
        destination = self.get_input('hostname')
        if self.has_input('username') or self.has_input('port'):
            destination = {'hostname': destination,
                           'username': self.get_input('username'),
                           'port': self.get_input('port')}
        queue = self.get_input('queue')
        self.set_output('queue', tej.RemoteQueue(destination, queue))


class RemoteJob(object):
    def __init__(self, queue, job_id):
        self.queue = queue
        self.job_id = job_id

    def get_monitor_id(self):
        # Identifier for the JobMonitor
        return '%s/%s/%s' % (self.queue.destination_string,
                             self.queue.queue,
                             self.job_id)


class Job(Module):
    """A reference to a job in a queue.

    Objects represented by this type only represent completed jobs, since else,
    the creating module would have failed/suspended.

    You probably won't use this module directly since it references a
    pre-existing job by name.
    """
    _input_ports = [('id', '(basic:String)'),
                    ('queue', Queue)]
    _output_ports = [('job', '(org.vistrails.extra.tej:Job)'),
                     ('exitcode', '(basic:Integer)')]

    job = None

    def compute(self):
        queue = self.get_input('queue')
        job_id = self.get_input('id')

        # Check job status
        try:
            status, arg = queue.status(job_id)
        except tej.JobNotFound:
            raise ModuleError(self, "Job not found")

        # Create job object
        self.job = RemoteJob(queue=queue, job_id=job_id)

        if status == tej.RemoteQueue.JOB_DONE:
            self.set_output('job', self.job)
            self.set_output('exitcode', arg)
        elif status == tej.RemoteQueue.JOB_RUNNING:
            raise ModuleSuspended(self, "Remote job is running",
                                  monitor=self.job)
        else:
            raise ModuleError(self, "Invalid job status %r" % status)


class SubmitJob(JobMixin, Job):
    """Starts a job on a server.

    Thanks to the suspension/job tracking mechanism, this module does much more
    than start a job. If the job is running, it will suspend again. If the job
    is finished, you can obtain files from it.
    """
    _input_ports = [('job', '(basic:Directory)'),
                    ('script', '(basic:String)',
                     {'optional': True, 'defaults': "['start.sh']"}),
                    ('id', '(basic:String)',
                     {'optional': True})]

    def job_id(self, params):
        return self.job.get_monitor_id()

    def job_read_inputs(self):
        return {'destination': self.get_input('queue').destination_string,
                'queue': self.get_input('queue').queue,
                'job_id': self.get_input('id')}

    def job_start(self, params):
        queue = tej.RemoteQueue(params['destination'], params['queue'])
        queue.submit(params['job_id'], self.get_input('directory'))
        return params

    def job_get_monitor(self, params):
        return self.job


_modules = [Queue, Job, SubmitJob]
