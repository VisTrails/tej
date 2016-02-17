#!/bin/sh

. .travis/utils.sh

run_lines<<'EOF'
sudo apt-get update -qq
sudo apt-get install -qq openssh-client openssh-server
pip install 'git+https://github.com/remram44/rpaths.git#egg=rpaths'
python setup.py install
EOF

.travis/setup_ssh.sh
