#!/usr/bin/env python

"""A very simple mail tool that I use on a Synology NAS to send email,
where an usuable "mail" command line tool doesn't seem to be available
via ipkg, in particular if I don't want to install a local SMTP server.
"""

import sys
from optparse import OptionParser
import smtplib
from email.mime.text import MIMEText


def main():
    parser = OptionParser()
    parser.add_option("-s", dest="subject", help="Subject")
    parser.add_option("-f", dest="from_", help="From address")
    parser.add_option("--host", dest="host", help="SMTP Host")
    parser.add_option("--port", dest="port", help="SMTP Port", default=25)
    parser.add_option("-q", dest="quiet", help="Be quiet.", default=False)

    (options, recipients) = parser.parse_args()

    if not recipients:
        print "No recipients specified."
        return 1

    stdin = sys.stdin.read()
    if not stdin.strip():
        if not options.quiet:
            print "No stdin text, not sending message."
        return 1

    smtp = smtplib.SMTP()
    smtp.connect(options.host, options.port)
    for recipient in recipients:
        msg = MIMEText(stdin)
        msg['Subject'] = options.subject
        msg['From'] = options.from_
        msg['To'] = recipient
        smtp.sendmail(options.from_, [recipient], msg.as_string())
    smtp.quit()



if __name__ == '__main__':
    sys.exit(main() or 0)