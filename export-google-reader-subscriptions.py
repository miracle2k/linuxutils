#!/usr/bin/env python
# coding: utf8
"""Export your Google Reader subscriptions to OPML format.

2011 by Michael Elsdörfer. Consider this public domain.


This script depends on the libgreader library:

     https://github.com/askedrelic/libgreader/

Which be installed via:

     $ easy_install libgreader


Usage:

     $ export-google-reader-subscriptions username password

If the password is not given, it is queried via stdin. The final
OPML is written to stdout.
"""

import sys
import xml.etree.ElementTree as ET
try:
    import libgreader
except ImportError:
    print "libgreader not installed. Use easy_install libgreader"
else:
    from libgreader import GoogleReader, ClientAuthMethod


def main():
    if len(sys.argv) <= 1 or len(sys.argv) > 3:
        print("Usage: %s username [password]" % (sys.argv[0]))
        return 1

    username = sys.argv[1]
    if len(sys.argv) == 2:
        sys.stderr.write('Password for %s: ' % username)
        password = raw_input()
    else:
        password = sys.argv[2]

    auth = ClientAuthMethod(username, password)
    reader = GoogleReader(auth)

    root = ET.Element('opml')
    head = ET.SubElement(root, 'head')
    ET.SubElement(head, 'title').text = \
        '%s subscriptions in Google Reader' % username
    body = ET.SubElement(root, 'body')

    category_els = {}

    reader.buildSubscriptionList()
    for feed in reader.getSubscriptionList():
        if feed.getCategories():
            for category in feed.getCategories():
                # Create category element
                if not category.id in category_els:
                    category_el = ET.SubElement(body, 'outline')
                    category_el.set('text', category.label)
                    category_el.set('title', category.label)
                    category_els[category.id] = category_el
                make_feed_el(feed, category_els[category.id])
        else:
            make_feed_el(feed, body)

    tree = ET.ElementTree(root)
    tree.write(sys.stdout, xml_declaration=True)


def make_feed_el(feed, parent):
    feed_el = ET.SubElement(parent, 'outline')
    feed_el.set('text', feed.title)
    feed_el.set('title', feed.title)
    feed_el.set('type', 'rss')
    feed_el.set('xmlUrl', feed.feedUrl)
    # seems to be always empty; possible a bug in libgreader?
    feed_el.set('htmlUrl', feed.siteUrl or '')


if __name__ == '__main__':
    sys.exit(main() or 0)
