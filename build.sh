#!/usr/bin/env bash
# exit on error
set -o errexit

pip install --upgrade pip
# Install the most memory-intensive packages first with --no-cache-dir
pip install torch --no-cache-dir
# Now install the rest of the requirements
pip install -r requirements.txt
