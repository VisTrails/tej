Changelog
=========

0.3 (???)
---------

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
