#!/usr/bin/env sh

mongoose -a /dev/stdout -e /dev/stderr -I `which php5-cgi` -d yes -r $(pwd)