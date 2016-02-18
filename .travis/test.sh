#!/bin/sh

set -eux

export TEJ_DESTINATION="ssh://127.0.0.1:10022"

case "$TEST_MODE"
in
    tests)
        python tests
    ;;
    coverage)
        coverage run --source=tej --branch tests/__main__.py
        codecov
    ;;
    flake8)
        flake8 --ignore=E731 tej tests
    ;;
esac
