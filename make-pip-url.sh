#!/usr/bin/env bash

#
# Print a pip url to stdout.
#
#    $ ./script.sh miracle2k/webassets
#    pip -e git://github.com/webassets.git@be5add0032932e0af0e066d80a1ece30cc21dba9#egg=webassets
#
# Update the "requirements.pip" file with the new commit hash.
#
#    $ ./script.sh miracle2k/webassets requirements.pip
#
# If a file named $DEFAULT_FILENAME exists, the second syntax will
# automatically be chosen, unless "-" is passed for the filename.
#

DEFAULT_FILENAME='requirements.pip'

usage()
{
cat << EOF
usage: $0 username/repo [filename]

Fetch the latest revision of the given repository, and output
a pip url. If a filename is given, the url already in that file
will be updated with the new revision, or be added.
EOF
}

# Handle the arguments
if [ ! $1 ]
then
    usage
  	exit 1
fi

QUERY=$1
FILENAME=$2
REPO=${QUERY#*/}
USER=${QUERY%/*}

# Fetch the current revision
HASH=$(curl -s http://github.com/api/v2/yaml/repos/show/$QUERY/branches | grep "  master" | awk '{ print $2 }')
if [ ! $HASH ]; then
    echo "Unable to find commit hash $QUERY at branch master";
    exit 1;
fi

# Build the pip url
URL="-e git://github.com/$QUERY.git@$HASH#egg=$REPO"

# http://stackoverflow.com/questions/407523/bash-escape-a-string-for-sed-search-pattern
escape() { echo "$1" | sed -e 's/\(\.\|\/\|\*\|\[\|\]\|\\\)/\\&/g'; }

# If a filename was given, or the default file
# exists in the wd, update.
if  [ "$FILENAME" -o -f "$DEFAULT_FILENAME" ] && [ ! "$FILENAME" == "-" ]
then
    # If we're here because of DEFAULT_FILENAME, use it subsequently
    [ ! $FILENAME ] && FILENAME=$DEFAULT_FILENAME

    # Need to quote the variable before passing to escape, and I
    # haven't found a way to do this inline.
    e_url=$(escape "$URL")
    e_query=$(escape "$QUERY")

    # The string we search for to determine which line to replace
    search="^.*github.com\/$e_query.*\$"

    if grep -q "$search" "$FILENAME"; then
        sed -i "s/$search/$e_url/" $FILENAME
        echo "$FILENAME (updated)"
    else
        echo "$URL" >> $FILENAME
        echo "$FILENAME (appended)"
    fi
else
    # Otherwise, simply output the url
    echo "pip install $URL"
fi

