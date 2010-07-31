"""
    Usage: %s source.db target.db new_component
    
    Copies all tickets, ticket changes and ticket attachments from the source database
    to the target database, and updates the 'component' field on each ticket.
    
    * 'component' is replaced and 'milestone' removed from tickets. Customize the
      script if you don't / need this behaviour.
    * Make backups yourself!
    * No attempt is made to preserve ticket IDs from the source.
    * Ignores the ticket_custom table - not sure what it's for, it always
      seems to be empty.
    * Tries to be as generic as possible, but makes some assumptions about the
      database schema when accessing columns via indices.
    * Expects both databases to be based on the same trac-version, i.e.
      have the same schema.
"""

import sys, os
from pysqlite2 import dbapi2 as sqlite

def main(argv):
    try:
        source_file, dest_file, new_component = argv
    except ValueError:
        print "Usage: %s source.db target.db new_component" % os.path.basename(sys.argv[0])
        return 1

    # connect to databases
    source_conn = sqlite.connect(source_file)
    source_cur = source_conn.cursor()
    dest_conn = sqlite.connect(dest_file)
    dest_cur = dest_conn.cursor()

    qmarks = lambda seq: ','.join(['?' for r in seq])
    try:
        # go through tickets in source
        tickets = source_cur.execute('SELECT * FROM ticket;')
        for ticket in tickets:
            # delete the id column - will get a new id
            old_id = ticket[0]
            ticket = list(ticket[1:])
            # reset values of component and milestone rows
            ticket[4-1] = new_component     # component
            ticket[11-1] = None               # milestone
            # insert ticket into target db
            print "copying ticket #%s" % old_id
            dest_cur.execute('INSERT INTO ticket '+
                                '('+(','.join([f[0] for f in source_cur.description[1:]]))+') '+
                                'VALUES('+qmarks(ticket)+')',
                            ticket)
            new_id = dest_cur.lastrowid

            # parameters: table name, where clause, query params, id column index, table repr, row repr index
            def copy_table(table, whereq, params, id_idx, trepr, rrepr_idx):
                cur = source_conn.cursor()
                try:
                    cur.execute('SELECT * FROM %s WHERE %s'%(table, whereq), params)
                    for row in cur:
                        row = list(row)
                        row [id_idx] = new_id
                        print "\tcopying %s #%s"%(trepr, row [rrepr_idx])
                        dest_cur.execute('INSERT INTO %s VALUES(%s)'%(table,qmarks(row)), row)
                finally:
                    cur.close()

            # copy ticket changes
            copy_table('ticket_change',
                       'ticket=?', (old_id,),
                       0, 'ticket change', 1)
            # copy attachments
            copy_table('attachment',
                       'type="ticket" AND id=?', (old_id,),
                       1, 'attachment', 2)

        # commit changes
        dest_conn.commit()
    finally:
        dest_conn.close()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))