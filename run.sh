#!/bin/bash
cd /home/ubuntu/Desktop/ECE1779-A2-worker/ECE1779A2
./venv/bin/gunicorn --bind 0.0.0.0:5000 --workers=8 --worker-class gevent --access-logfile access.log --error-logfile error.log app:webapp
