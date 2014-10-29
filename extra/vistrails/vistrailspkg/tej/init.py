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


JobDescr = namedtuple('JobDescr', ['queue', 'job'])


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

    def compute(self):
        queue = self.get_input('queue')
        job_id = self.get_input('id')

        # Check job status
        try:
            status, arg = queue.status(job_id)
        except tej.JobNotFound:
            raise ModuleError(self, "Job not found")

        job_descr = JobDescr(queue=queue, id=job_id)

        if status == tej.RemoteQueue.JOB_DONE:
            self.set_output('job', job_descr)
            self.set_output('exitcode', arg)
        elif status == tej.RemoteQueue.JOB_RUNNING:
            raise ModuleSuspended(self, "Remote job is running",
                                  monitor=self.job_get_monitor())
        else:
            raise ModuleError(self, "Invalid job status %r" % status)

    def job_get_monitor(self):
        todo # FIXME : Can't figure out what goes in here
        # The Job class doesn't seem to match what JobMonitor calls


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

    def compute(self):
        queue = self.get_input('queue')
        identifier = self.get_input('id')

        queue.submit(identifier, self.get_input('job'),
                     self.get_input('script'))

    job_get_monitor = Job.job_get_monitor


_modules = [Queue, Job, SubmitJob]
