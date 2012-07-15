#!/usr/bin/env python
"""I like to have a LOCAL_TODO file for each of my programming projects
that is not under version control and that serves as a whiteboard for notes,
and ideas. It also like to put a "next steps" list there as a quick brain
refresh for when I come back to the project after some time.

Because these files are  not under version control, I use Dropbox to sync them
across machines (also serves as a backup).

What this script does is create such a file in a shared folder (this is a
folder that would be managed by Dropbox), and then links this file into the
current directory. If there is already a LOCAL_TODO file in the current
directory, it will be moved to the shared folder.
"""

import os
import sys
import glob
from os import path
import json
import docopt    # http://pypi.python.org/pypi/docopt/


docstring = """
Manage LOCAL_TODO files.

In the default invocation, will create or move an existing LOCAL_TODO
file to a shared folder, then create a link to it in it's original
place.

Usage:
    localtodo.py [--to <path>] [-s <name>] [<name>]
    localtodo.py --delete <name>

Options & Arguments:
    -h, --help   Show this screen.

    <name>       The project name. If not given, the name of the
                 containing folder will be used.
    --to <path>  Where to create the file. The first time you use
                 the script you will have to specify this. It will
                 subsequently be saved in a ~/.localtodo file.
    -s <name>, --sub <name>
                 Create a sub-TODO file. The name will be appended
                 as a suffix, like this: "LOCAL_TODO.docs".
                 The default invocation will link all such existing
                 TODO files into the local directory.
    --delete <name>
                 Delete an existing LOCAL_TODO file for the given
                 project name.
"""


CONFIG_FILE = '~/.localtodo'
TODOFILE_NAME = 'LOCAL_TODO'
SUBFILE_NAME = 'LOCAL_TODO.%s'


class ExitCodeError(Exception):
    def __init__(self, code):
        self.code = code


def main(argv):
    args = docopt.docopt(docstring, argv[1:])

    # Open config file
    config = {}
    if path.exists(path.expanduser(CONFIG_FILE)):
        with open(path.expanduser(CONFIG_FILE), 'r') as f:
            config = json.load(f)

    # Determine target directory
    target_directory = args['--to'] or config.get('directory', None)
    if not target_directory:
        print 'You need to use --to at least once to tell me where '\
              'to store the todo files.'
        return 1
    else:
        config['directory'] = target_directory
        with open(path.expanduser(CONFIG_FILE), 'w') as f:
            json.dump(config, f)

    # Implement --delete mode
    if args['--delete']:
        target_file = path.join(target_directory, args['--delete'])
        if args['--sub']:
            target_file = "%s.%s" % (target_file,  args['--sub'])
        if not path.exists(target_file):
            print 'Error: No such file: %s' % target_file
            return 2
        os.unlink(target_file)
        return

    # Normal sync mode
    project = args['<name>']
    subfile = args['--sub']
    if not project:
        project = path.basename(path.abspath(os.curdir))

    env = {
    'target_directory': target_directory,
    'established_links': []
    }
    try:
        if subfile:
            sync_todo(env, project, subfile)
        else:
            # Sync the main file
            sync_todo(env, project)
            # Find all existing sub-todo files, both in remote
            # and in local dir, sync them all.
            for sub in findsubs(path.join(target_directory,
                                      "%s.*" % project)):
                sync_todo(env, project, sub)
            for sub in findsubs(SUBFILE_NAME % '*'):
                sync_todo(env, project, sub)
    except ExitCodeError, e:
        return e.code

    # Print summery of state
    print
    print "I have established the following links for you:"
    for source, target in set(env['established_links']):
        print '  %s --> %s' % (source, target)


def findsubs(expr):
    """Helper that extracts sub-todo suffixes from a list of
    glob results."""
    for filename in glob.glob(expr):
        basename, subname = path.splitext(path.basename(filename))
        if subname:
            yield subname[1:]  # remove the dot


def sync_todo(env, project, subfile=None):
    """Ensure that the todo file identified by ``project`` and
    ``subfile`` is setup correctly (exists in local dir, links to
    target dir).

    If not the case, try to make it so.
    """
    target_directory = env['target_directory']

    # Determine target file
    target_file = path.join(target_directory, project)
    if subfile:
        target_file = "%s.%s" % (target_file, subfile)

    # Determine source file
    if subfile:
        source_file = path.join(os.curdir, SUBFILE_NAME % subfile)
    else:
        source_file = path.join(os.curdir, TODOFILE_NAME)

    # See what we have to do
    if path.exists(source_file) and path.exists(target_file):
        if path.realpath(source_file) == target_file:
            env['established_links'].append((source_file, target_file))
            return
        print '%s exists, but so does %s\nMaybe you want to call with '\
              '"--delete %s" to delete the target.' % (
                  target_file, source_file, project)
        raise ExitCodeError(2)

    # If there is a local file, move it to the target
    if path.exists(source_file):
        assert not path.islink(source_file)  # TODO: transparently replace links
        print 'Moving %s to %s' % (source_file, target_file)
        os.rename(source_file, target_file)
    elif not path.exists(target_file):
        print 'Creating new empty file %s' % (target_file,)
        with open(target_file, 'w'):
            pass
    else:
        print 'Found existing file %s' % (target_file,)

    # Create the link
    # To use the relative path: path.relpath(target_file, path.dirname(source_file))
    os.symlink(path.abspath(target_file), source_file)
    env['established_links'].append((source_file, target_file))


if __name__ == '__main__':
    sys.exit(main(sys.argv) or 0)
