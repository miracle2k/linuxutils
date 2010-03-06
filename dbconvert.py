#!/usr/bin/env python
"""
Script to convert between different databases.

Written against SQLAlchemy 6.1beta.

Based on code from:
http://www.tylerlesmann.com/2009/apr/27/copying-databases-across-platforms-sqlalchemy/

TODO: Not using the ORM is likely faster, but more extensive to write;
We'd need to construct queries manually; also, even with the ORM, there
are probably some SQLAlchemy-related optimizations that could be employed
to speed up the the processing of large tables (expunge_all?).

TODO: Quite frequently, schema conversion doesn't work because SQLAlchemy is
quite strict about schemas. For example, SQLite has no LONGTEXT column, and
MySQL requires a fixed length VARCHAR. Does requirements are not automatically
bridged. Possible a way could be provided for the user to define the mapper
him/herself. Note that this basically is only a schema creation issue. You
can already workaround such a error by defining the target table manually.
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
        # Note that yield only affects the number of ORM objects generated
        # by SA; The stupid MySQLdb backend still fetches all rows at once.
        # Try OurSQL. References for this:
        # * http://www.mail-archive.com/sqlalchemy@googlegroups.com/msg17389.html)
        # * http://stackoverflow.com/questions/2145177/is-this-a-memory-leak-a-program-in-python-with-sqlalchemy-sqlite
        for record in source.query(table).yield_per(getattr(options, 'yield')):
            data = dict(
                [(str(column), getattr(record, column)) for column in columns]
            )
            if options.merge:
                # TODO: Can be use load=False here? And should we?
                destination.merge(NewRecord(**data))
            else:
                destination.add(NewRecord(**data))

            i += 1

            if (options.flush and i % options.flush == 0):
                destination.flush()
            if (options.commit and i % options.commit == 0):
                destination.commit()

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
    parser.add_option('--merge', dest="merge", action='store_true',
                      help="merge with existing data based on primary key; "+
                           "use if the target table already has rows; up to "+
                           "15 times slower.")
    parser.add_option('-y', '--yield', dest="yield", default=4000,
                      type="int", metavar="NUM",
                      help="number of source rows to pull into memory in one "+
                            "batch; some backends like MySQLdb still fetch "+
                            "everything anyway (default: %default)")
    parser.add_option('-f', '--flush', dest="flush", default=10000,
                      type="int", metavar="NUM",
                      help="number of rows to cache in memory before sending "+
                           "queries to the destination database "+
                           "(default: %default)")
    parser.add_option('-c', '--commit', dest="commit", default=None,
                      type="int", metavar="NUM",
                      help="number of rows after which to commit and start a "+
                           "new transaction; implies a flush (default: "+
                           "only commit when done)")
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