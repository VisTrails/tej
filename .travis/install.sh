#!/bin/sh

set -eux

case "$TEST_MODE"
in
    tests|coverage)
        sudo apt-get update -qq
        sudo apt-get install -qq openssh-client openssh-server
        pip install -U pip setuptools
        if [ "$TEST_MODE" = coverage ]; then
            pip install coverage codecov
            pip install -e .
        else
            pip install .
        fi

        .travis/setup_ssh.sh
    ;;
    flake8)
        pip install flake8
    ;;
esac
