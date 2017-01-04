from __future__ import absolute_import, division, unicode_literals


__all__ = ['Error', 'InvalidDestination', 'QueueDoesntExist',
           'QueueLinkBroken', 'QueueExists', 'JobAlreadyExists', 'JobNotFound',
           'JobStillRunning', 'RemoteCommandFailure']


class Error(Exception):
    """Base class for exceptions.
    """


class InvalidDestination(Error):
    """Invalid SSH destination.
    """
    def __init__(self, msg="Invalid destination"):
        super(InvalidDestination, self).__init__(msg)


class QueueDoesntExist(Error):
    """Queue doesn't exist on the server.

    `submit` and `setup` will create a queue on the server, but other commands
    like `status` and `kill` expect it to be there.
    """
    def __init__(self, msg="Queue doesn't exist on the server"):
        super(QueueDoesntExist, self).__init__(msg)


class QueueLinkBroken(QueueDoesntExist):
    """The chain of links is broken.

    There is a link file on the server that doesn't point to anything.
    """
    def __init__(self, msg="Queue link chain is broken"):
        super(QueueLinkBroken, self).__init__(msg)


class QueueExists(Error):
    """The queue whose creation was requested already exists.

    A `force` argument (``--force``) is provided to replace it anyway.
    """
    def __init__(self, msg="Queue already exists"):
        super(QueueExists, self).__init__(msg)


class JobAlreadyExists(Error):
    """A job with this name already exists on the server; submission failed.
    """
    def __init__(self, msg="Job already exists"):
        super(JobAlreadyExists, self).__init__(msg)


class JobNotFound(Error):
    """A job with this name wasn't found on the server.
    """
    def __init__(self, msg="Job not found"):
        super(JobNotFound, self).__init__(msg)


class JobStillRunning(Error):
    """An operation failed because the target job is still running.
    """
    def __init__(self, msg="Job is still running"):
        super(JobStillRunning, self).__init__(msg)


class RemoteCommandFailure(Exception):
    """A failure that happened on the server.
    """
    def __init__(self, msg=None, command=None, ret=None):
        if msg is None:
            msg = "Command %r failed with status %d" % (command, ret)
        super(RemoteCommandFailure, self).__init__(msg)
        self.command = command
        self.ret = ret
