#!/usr/bin/env python
"""
Script to convert between different databases.

Written against SQLAlchemy 6.1beta.

Based on code from:
http://www.tylerlesmann.com/2009/apr/27/copying-databases-across-platforms-sqlalchemy/
"""

import optparse
import sys
import time
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


def make_session(connection_string):
    engine = create_engine(connection_string, echo=False, convert_unicode=True)
    Session = sessionmaker(bind=engine)
    return Session(), engine


def pull_data(from_db, to_db, options):
    source, sengine = make_session(from_db)
    smeta = MetaData(bind=sengine)
    destination, dengine = make_session(to_db)

    print 'Pulling schemas from source server'
    smeta.reflect(only=options.tables)

    for name, table in smeta.tables.iteritems():
        print 'Processing table "%s"' % name
        if options.create_tables:
            print '...Creating table on destination server'
            table.metadata.create_all(dengine)
        NewRecord = quick_mapper(table)
        columns = table.columns.keys()

        num_records = source.query(table).count()
        i = 0
        start = time.time()
        for record in source.query(table).all():
            data = dict(
                [(str(column), getattr(record, column)) for column in columns]
            )
            destination.merge(NewRecord(**data))
            i += 1

            now = time.time()
            done = i/float(num_records)
            sys.stderr.write('...Transferring record %d/%d (%d%%), %ds elapsed, %ds estimated\r' % (
                i, num_records, done*100, now-start, (now-start)/done))
            sys.stderr.flush()
        sys.stderr.write("\n");
        print '...Transferred %d records in %f seconds' % (i, time.time() - start)
    print '...Committing changes'
    destination.commit()


def get_usage():
    return """usage: %prog [options] FROM TO

FROM/TO syntax: driver://user[:password]@host[:port]/database)
Example: mysql://root@db2:3307/reporting"""


def quick_mapper(table):
    Base = declarative_base()
    class GenericMapper(Base):
        __table__ = table
    return GenericMapper


def main():
    parser = optparse.OptionParser(usage=get_usage())
    parser.add_option('-t', '--table', dest="tables", action="append",
                      help="comma only this table (can be given multiple times)",
                      metavar="NAME")
    parser.add_option('--skip-schema', dest="create_tables", default=True,
                      action='store_false',
                      help="do not create tables in the destination database")
    options, args = parser.parse_args(sys.argv[1:])

    if len(args) < 2:
        parser.print_usage()
        print >>sys.stderr, "error: you need to specify FROM and TO urls"
        return 1
    elif len(args) > 2:
        parser.print_usage()
        print >>sys.stderr, "error: unexpected arguments: %s" % ", ".join(args[2:])
        return 1
    else:
        from_url, to_url = args

    pull_data(
        from_url,
        to_url,
        options,
    )


if __name__ == '__main__':
    sys.exit(main() or 0)