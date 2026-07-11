#!/bin/bash
# Vercel build step: collect static assets for WhiteNoise to serve.
# Runs in an isolated build env (separate from the @vercel/python function
# build), so requirements must be installed here too.
python3 -m pip install -r requirements.txt
python3 manage.py collectstatic --noinput --clear
