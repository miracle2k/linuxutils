#!/usr/bin/env python
"""
Script to convert between different databases.

Written against SQLAlchemy 6.1beta.

Based on code from:
http://www.tylerlesmann.com/2009/apr/27/copying-databases-across-platforms-sqlalchemy/
"""

import getopt
import sys
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


def make_session(connection_string):
    engine = create_engine(connection_string, echo=False, convert_unicode=True)
    Session = sessionmaker(bind=engine)
    return Session(), engine


def pull_data(from_db, to_db, tables, create_schema):
    source, sengine = make_session(from_db)
    smeta = MetaData(bind=sengine)
    destination, dengine = make_session(to_db)

    print 'Pulling schemas from source server'
    smeta.reflect(only=tables or None)

    for name, table in smeta.tables.iteritems():
        print 'Processing', name
        if create_schema:
            print 'Creating table on destination server'
            table.metadata.create_all(dengine)
        NewRecord = quick_mapper(table)
        columns = table.columns.keys()
        print 'Transferring records'
        for record in source.query(table).all():
            data = dict(
                [(str(column), getattr(record, column)) for column in columns]
            )
            destination.merge(NewRecord(**data))
    print 'Committing changes'
    destination.commit()


def print_usage():
    print """
Usage: %s -f source_server -t destination_server table [--all] [--skip-schema] [table ...]
    -f, -t = driver://user[:password]@host[:port]/database

Example: %s -f oracle://someuser:PaSsWd@db1/TSH1 \\
    -t mysql://root@db2:3307/reporting table_one table_two
    """ % (sys.argv[0], sys.argv[0])


def quick_mapper(table):
    Base = declarative_base()
    class GenericMapper(Base):
        __table__ = table
    return GenericMapper


def main():
    optlist, tables = getopt.getopt(sys.argv[1:], 'f:t:', ['all', 'skip-schema'])

    options = dict(optlist)
    if '-f' not in options or '-t' not in options or not (
        bool(tables) ^ bool('--all' in options)):
        print_usage()
        return 1

    pull_data(
        options['-f'],
        options['-t'],
        tables,
        not '--skip-schema' in options
    )


if __name__ == '__main__':
    sys.exit(main() or 0)