Changelog
=========

0.5 (2016-12-23)
----------------

Behavior change:
* Logging on tej.server now happens with level INFO (was WARNING).

Bugfixes:
* stdout is now recorded correctly on PBS
* Fix escaping, making tej work when the queue is a relative path
* Don't log the password

Features:
* `submit()`'s `script` parameter now accepts a full command in addition to a filename
* Expose `_ssh_client()`, allowing children classes to override the SSHClient settings
* Make status constants strings, which means they can be directly compared with `info['status']` from `list()`

0.4 (2016-12-08)
----------------

Bugfixes:
* Better quoting (useful if using spaces or unusual characters in paths)
* Test runner no longer hides logging messages

Features:
* Add `queue.get_scp_client()`, useful to transfer files using the same connection
* Add optional password to destination string

0.3 (2016-02-20)
----------------

Bugfixes:
* Fix typo: `InvalidDestionation` -> `InvalidDestination`
* Avoid using argparse's 'parents' features (see [PY#23058](https://bugs.python.org/issue23058))
* Fix formatting of dates showing a warning

Features:
* Add runtime selection to API, command-line (`--runtime`), and auto-detect by default
* Add support for PBS: jobs will be run using qsub

0.2.3 (2015-08-07)
------------------

Bugfixes:
* Fix having multiple `tej.log` files on the server

0.2.2 (2015-07-16)
------------------

VisTrails packages taken out, moved to VisTrails' repository.

0.2.1 (2015-04-06)
------------------

Bugfixes:
* Fix package compatibility with newer versions of pip

0.2 (2015-04-06)
----------------

Features:
* VisTrails package
* More reliable shell scripts (set -e)

0.1 (2014-11-21)
----------------

Initial version of tej, job submission system intended to be used as a backend for VisTrails' job submission capabilities. Python 2 & 3 compatible, multiple backends (integrate with PBS & other servers, but also run on plain servers).
