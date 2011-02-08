#!/usr/bin/env bash

# Nautilus script to send files to your Kindle. Requires the
# ``sendemail`` command.
#
# 2011 by Michael Elsdörfer. Licensed under MIT.
#
# For now, copy this to your ~/gnome2/nautilus-scripts folder.
#
# In the future, integration into nautilus-sendto would be cool. For a code
# example, see: nautilus-sendto-plugin @ github.com/blackskad/empathy

# Expects a ~/.sendtokindlerc file in ini format with the following values:
#
#    SENDER = <YOUR_EMAIL>
#    KINDLE_USER = <YOUR_KINDLE_USERNAME>
#    SEND_FREE = <YES|no>
#    SMTP_HOST = <HOSTNAME>
#    SMTP_USER = <USERNAME>
#    SMTP_PASS = <PASSWORD>
#    SMTP_USE_TLS = <yes|NO>

# The sender email address must be in your Amazon whitelist. Configure it at:
#    https://www.amazon.com/gp/digital/fiona/manage

#
# TODO: Rewrite this in Python or C, with a UI, allowing to select options
# like whether to convert, or whether to send via free or pay. Also, we can
# send multiple documents in one email.
#


if [ -r ~/.sendtokindlerc ]; then
    . ~/.sendtokindlerc
else
    notify-send -u normal -t 5 -i error "Configuration file does not exist!"
    exit 1
fi

if [ "$SEND_FREE" == "yes" ]; then
    kindle_domain='free.kindle.com'
fi
kindle_to="$KINDLE_USER@${kindle_domain:="kindle.com"}"


for arg; do
    file="$arg"
    if [ -d "$file" ]; then
        notify-send -u normal -t 5 -i error "Not sending \"$file\", is a directory."
        continue
    fi

    stdout=$(sendemail -f "$SENDER" -t "$kindle_to" -m "convert" -u "convert" -s "$SMTP_HOST" -xu "$SMTP_USER" -xp "$SMTP_PASS" -o tls=${SMTP_USE_TLS:="no"} -a "$file" 2>&1)
    echo "bla"
    if [ $? -eq 0 ]; then
        shortname=$(basename "$file")
        notify-send -u normal -t 1 -i info "Send to your Kindle: \"$shortname\""
    else
        error=$(echo "$stdout" | sed "s/^.*=> //")
        notify-send -u normal -t 5 -i error "Could not send: $error"
        exit 1
    fi
done
