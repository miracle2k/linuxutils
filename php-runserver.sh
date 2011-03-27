#!/usr/bin/env sh

CONF=""
if [ -x "mongoose.conf" ]; then
    CONF="mongoose.conf"
fi

mongoose -a /dev/stdout -e /dev/stderr -I `which php5-cgi` -d yes -r $(pwd)$* $CONF