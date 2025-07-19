#!/usr/bin/env bash
# exit on error
set -o errexit

# Upgrade pip and setuptools
pip install --upgrade pip setuptools wheel

# Install dependencies from the cleaned requirements.txt
pip install -r requirements.txt --no-cache-dir
