#!/usr/bin/env python
#
# ispmailadmin.py
#
# Helps maintain virtual user accounts for server that are configured
# as suggested in the workaround.org isp-mail tutorial.
#
# (C) 2007 Christoph Haas <email@christoph-haas.de>
# License: MIT
#
# Port to SQLAlchemy 0.6 by Michael Elsdoerfer <michael@elsdoerfer.com>
#

import os
import cmd
import readline
import sys

from sqlalchemy import *
from sqlalchemy.exceptions import *
from sqlalchemy.orm import mapper, sessionmaker, relation

# Database URI
from config import db_uri
sql_debugging_enabled = False

class Console(cmd.Cmd):

    def __init__(self):
        cmd.Cmd.__init__(self)
        self.prompt = "=>> "
        self.intro  = "Welcome to the ispmail console!"  ## defaults to None

    ## Command definitions ##
    def do_hist(self, args):
        """Print a list of commands that have been entered"""
        print self._hist

    def do_exit(self, args):
        """Exits from the console"""
        return -1

    ## Command definitions to support Cmd object functionality ##
    def do_EOF(self, args):
        """Exit on system end of file character"""
        return -1

    def do_help(self, args):
        """Get help on commands
           'help' or '?' with no arguments prints a list of commands for which help is available
           'help <command>' or '? <command>' gives help on <command>
        """
        ## The only reason to define this method is for the help text in the doc string
        cmd.Cmd.do_help(self, args)

    ## Override methods in Cmd object ##
    def preloop(self):
        """Initialization before prompting user for commands.
           Despite the claims in the Cmd documentaion, Cmd.preloop() is not a stub.
        """
        cmd.Cmd.preloop(self)   ## sets up command completion
        self._hist    = []      ## No history yet
        self._domainid  = None    ## Current domain

        # Set up SQLAlchemy for database access
        engine = create_engine(db_uri)
        Session = sessionmaker(bind=engine, autocommit=True)
        self.ctx = Session()
        meta = MetaData()
        meta.bind = engine
        engine.echo = sql_debugging_enabled

        domains_table = Table('domains', meta,
            Column('id', Integer, primary_key=True),
            Column('name', Unicode)
            )

        aliases_table = Table('aliases', meta,
            Column('id', Integer, primary_key=True),
            Column('domain_id', Integer, ForeignKey('domains.id')),
            Column('source', Unicode),
            Column('destination', Unicode)
            )

        users_table = Table('users', meta,
            Column('id', Integer, primary_key=True),
            Column('domain_id', Integer, ForeignKey('domains.id')),
            Column('user', Unicode),
            Column('password', Unicode)
            )

        # Map tables to classes
        mapper(Domain, domains_table, order_by=domains_table.c.name,
                always_refresh=True,
                properties = {
                    'aliases' : relation(Alias, cascade="all, delete-orphan"),
                    'users' : relation(User, cascade="all, delete-orphan"),
                    }
                )
        mapper(Alias, aliases_table, order_by=aliases_table.c.source,
                always_refresh=True,
                properties = {
                    'domain' : relation(Domain)
                    })
        mapper(User, users_table, order_by=users_table.c.user,
                always_refresh=True,
                properties = {
                    'domain' : relation(Domain)
                    })

        # Print database statistics and by the way check if the database
        # connection works.
        try:
            number_of_domains = self.ctx.query(Domain).count()
            number_of_users = self.ctx.query(User).count()
            number_of_aliases = self.ctx.query(Alias).count()

            print "Connected to database (%s domains, %s users, %s aliases)" % (
                    number_of_domains, number_of_users, number_of_aliases)
        except DBAPIError, e:
            print "Database connection failed:", e
            print "Please check the 'db_uri' string at the beginning of this program."
            sys.exit(10)

    def do_domains(self, args):
        """Print list of virtual email domains. If an argument is given then it
           only lists domains starting with this string. If a unique ID or
           domain name is given then this domain is selected as current.
        """
        if args:
            try: # try if a numerical ID was given as argument
                domain = self.ctx.query(Domain).get(int(args)) # get the domain by it's ID
            except ValueError:
                # try to get the domain by name
                domain = self.ctx.query(Domain).filter_by(name=args).first()

            # Found a matching domain?
            if domain:
                self._domainid = domain.id
                self.prompt = "[%s] =>> " % (domain.name)
                return

            # No domain found. Show a list of domains

            # no direct hit. list domains that begin with the search string
            domains = self.ctx.query(Domain).filter(Domain.name.startswith(args[0]))

            if domains:
                for domain in domains:
                    print " [%3d]  %s" % (domain.id, domain.name)
                return

        else:
            # Show list of all domains
            domains = self.ctx.query(Domain).all()

            for domain in domains:
                print " [%3d]  %s" % (domain.id, domain.name)

    # Shortcut 'd' for domains
    do_d = do_domains

    def do_newdomain(self, args):
        """Create a new virtual domain
        """
        if not args:
            print "Please provide the name of the new domain as argument!"
            return

        # Check if domain exists already
        if self.ctx.query(Domain).filter_by(name=args).first():
            print "exists already..."
            return

        # Create a new domain
        # TODO: syntax checks
        new_domain = Domain()
        new_domain.name = args
        self.ctx.add(new_domain)
        self.ctx.flush()

    # Shortcut 'nd' for new domain
    do_nd = do_newdomain

    def do_deldomain(self, args):
        """Delete a domain
        """
        if not args:
            print "Please provide the name or the number of the domain as argument!"
            return

        # Try if a numerical ID was given as argument
        try:
            domain = self.ctx.query(Domain).get(int(args))
        except ValueError:
            domain = self.ctx.query(Domain).filter_by(name=args).first()

        if not domain:
            print "Domain not found"
            return

        print "Deleting domain '%s'" % domain.name
        domain.delete()
        self.ctx.flush()

        # If the domain was just selected then unselect it
        self._domainid = None
        self.prompt = "=>> "

    # Shortcut 'dd' for delete domain
    do_dd = do_deldomain

    def do_aliases(self, args):
        """Print list of virtual aliases. If an argument is given then it
           only lists aliases for email addresses starting with this string.
        """
        # Make sure a domain is selected
        if not self._domainid:
            print "Please select a domain first (enter its ID or domain name as a command)"
            return

        domain = self.ctx.query(Domain).get(self._domainid)
        print "Aliases in %s:" % domain.name
        for alias in domain.aliases:
            print " [%-2d] %-20s -> %s" % (alias.id, alias.source or '*', alias.destination)

    # Shortcut 'a' for aliases
    do_a = do_aliases

    def do_newalias(self, args):
        """Create a new alias in the current domain
        """
        # Make sure a domain is selected
        if not self._domainid:
            print "Please select a domain first (enter its ID or domain name as a command)"
            return

        if not args:
            print "newalias: source destination (source can be '*' for catchall)"
            return

        try:
            source, destination = args.split()
        except ValueError:
            print "newalias: source destination"
            return

        if '@' not in destination:
            print "The destination should contain an '@'."
            return

        print "New alias: %s -> %s" % (source, destination)
        if source=='*':
            source=''

        # Check if alias exists already
        if self.ctx.query(Alias).filter_by(domain_id=self._domainid, source=source, destination=destination).first():
            print "Alias exists already"
            return

        domain = self.ctx.query(Domain).get(self._domainid)

        new_alias = Alias()
        new_alias.source = source
        new_alias.destination = destination
        domain.aliases.append(new_alias)
        self.ctx.flush()

    # Shorcut 'na' for new alias
    do_na = do_newalias

    def do_delalias(self, args):
        """Delete an alias
        """
        if not args:
            print "Please provide either the ID or 'source destination' or 'source' as argument!"
            return

        # Attempt to get the alias by the numerical ID
        try:
            aliases = self.ctx.query(Alias).get(id=int(args))
        except ValueError:
            # Syntax: source destination
            if ' ' in args:
                source, destination = args.split(' ')
                aliases = self.ctx.query(Alias).filter_by(domain_id=self._domainid,
                        source=source, destination=destination).all()
            # Syntax: source
            else:
                aliases = self.ctx.query(Alias).filter_by(domain_id=self._domainid, source=args).all()

        if not aliases:
            print "No such alias found"
            return

        domain = self.ctx.query(Domain).get(self._domainid)
        for alias in aliases:
            print "Deleting alias %s -> %s" % (alias.source or '*', alias.destination)
            # Do not use "alias.delete()" because it will not update the
            # collections domain.aliases automatically in SQLAlchemy!
            domain.aliases.remove(alias)
        self.ctx.flush()

    # Shortcut 'da' for delete alias
    do_da = do_delalias

    def do_users(self, args):
        """Print list of virtual users. If an argument is given then it
           only lists users for email addresses starting with this string.
        """
        # Make sure a domain is selected
        if not self._domainid:
            print "Please select a domain first (enter its ID or domain name as a command)"
            return

        domain = self.ctx.query(Domain).get(self._domainid)
        print "Users in %s:" % domain.name
        for user in domain.users:
            print " [%-2d] %s" % (user.id, user.user)

    # Shortcut 'a' for users
    do_u = do_users

    def do_newuser(self, args):
        """Create a new user in the current domain
        """
        # Make sure a domain is selected
        if not self._domainid:
            print "Please select a domain first (enter its ID or domain name as a command)"
            return

        if not args:
            print "newuser: userpart password"
            return

        try:
            username, password = args.split()
        except ValueError:
            print "newuser: userpart password"
            return

        print "New user: %s (password: %s)" % (username, password)

        # Check if user exists already
        user = self.ctx.query(User).filter_by(domain_id=self._domainid, user=username).one()
        if user:
            print "User exists already, changing the password"
            user.password = func.md5(password)
            self.ctx.add(user)
            self.ctx.flush()
            return

        domain = self.ctx.query(Domain).get(self._domainid)

        new_user = User()
        new_user.user = username
        new_user.password = func.md5(password)
        domain.users.append(new_user)
        self.ctx.flush()

    # Shorcut 'nu' for new user
    do_nu = do_newuser

    def do_deluser(self, args):
        """Delete a user
        """
        if not args:
            print "Please provide either the ID or the userpart as argument!"
            return

        # Attempt to get the user by the numerical ID
        try:
            user = self.ctx.query(User).get(int(args))
        except ValueError:
            user = self.ctx.query(User).filter_by(domain_id=self._domainid, user=args).first()

        if not user:
            print "No such user found"
            return

        domain = self.ctx.query(Domain).get(self._domainid)
        print "Deleting user %s" % user.user
        # Do not use "user.delete()" because it will not update the
        # collections domain.users automatically in SQLAlchemy!
        domain.users.remove(user)
        self.ctx.flush()

    # Shortcut 'du' for delete user
    do_du = do_deluser


    def postloop(self):
        """Take care of any unfinished business.
           Despite the claims in the Cmd documentaion, Cmd.postloop() is not a stub.
        """
        cmd.Cmd.postloop(self)   ## Clean up command completion
        print "Exiting..."

    def precmd(self, line):
        """ This method is called after the line has been input but before
            it has been interpreted. If you want to modifdy the input line
            before execution (for example, variable substitution) do it here.
        """
        self._hist += [ line.strip() ]
        return line

    def postcmd(self, stop, line):
        """If you want to stop the console, return something that evaluates to true.
           If you want to do some post command processing, do it here.
        """

        return stop

    def emptyline(self):    
        """Do nothing on empty input line"""
        pass

    def default(self, line):
        """If the input is not a known command then it is assumed a certain
           domain is supposed to be selected. Domains can be given as their
           numerical ID or as the domain name itself.
        """
        pass

# Define SQLAlchemy mapper classes
class Domain(object):
    def __str__(self):
        return "Domain: %s (id=%s)" % (self.name, self.id)
class Alias(object):
    def __str__(self):
        return "Alias: %s -> %s" % (self.source, self.destination)
class User(object):
    def __str__(self):
        return "User: %s (%s)" % (self.user, self.password)

if __name__ == '__main__':
        console = Console()
        console.cmdloop() 

