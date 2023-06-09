#!/usr/bin/env bash

./tools/build-site.py
python3 -m http.server --directory site/ 8080 
