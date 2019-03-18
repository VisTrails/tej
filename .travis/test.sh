#!/bin/sh

set -eux

export TEJ_DESTINATION="ssh://127.0.0.1:10022"

case "$TEST_MODE"
in
    tests)
        python tests
    ;;
    coverage)
        export COVER="coverage run -p --source=tej,tests --branch"
        coverage run -p --source=tej,tests --branch tests/__main__.py
        coverage combine
        codecov
    ;;
    flake8)
        flake8 --ignore=W504,E731 .
    ;;
esac
