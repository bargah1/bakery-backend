#!/usr/bin/env bash
# exit on error
set -o errexit

pip install --upgrade pip

echo "Installing torch..."
pip install torch --no-cache-dir

echo "Installing dlib..."
pip install dlib --no-cache-dir

echo "Installing face-recognition..."
pip install face-recognition --no-cache-dir

echo "Installing remaining packages..."
pip install -r requirements.txt