#!/bin/bash
source /var/app/venv/staging-LQM1lest/bin/activate
cd /var/app/current
python manage.py migrate --noinput
mkdir -p /var/app/current/media/imagenes
chmod -R 777 /var/app/current/media