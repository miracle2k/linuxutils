#!/usr/bin/env python
"""This helps reconstructing a disk/snapshot hierarchy of a virtual machine,
in case you lose it's config file, or your VirtualBox.xml file.

Author: Michael Elsdoerfer <http://elsdoerfer.name>. Licensed under BSD.

How to use this:
 - Use --detail to inspect VDI headers.
 - If your VirtualBox.xml file is lost, use --xml to generate xml code for the
   media registry part.
 - If your VM specific xml is lost, it's thougher. The easiest way probably is:
      - Create a new machine with your base VDI.
      - Create snapshots matching the tree given by this script.
      - Edit the vm-specific XML file, and VirtualBox.xml, changing the UUIDs of
        the dummy snapshots with the UUIDs given to you by this script.
"""


import sys, os
import logging
from os import path
import optparse
from struct import unpack


logging.basicConfig(format='%(levelname)s: %(message)s')
log = logging.getLogger('')


VDI_TYPES = {
    1: 'Dynamic',
    2: 'Fixed',
    4: 'Differential',
}


class VDIHeader(object):
    version_minor = None
    version_major = None
    type = None
    flags = None
    size = None
    block_size = None
    num_blocks = None
    num_blocks_allocated = None
    uuid = None
    snapshot_uuid = None
    parent_uuid = None

    def __repr__(self):
        return "<VDIHeader: %s>" % self.uuid

    @property
    def version_str(self):
        return "%s.%s" % (self.version_major, self.version_minor)


class VDIError(Exception):
    pass



def read_int(f):
    return unpack('<i', f.read(4))[0]

def read_short(f):
    return unpack('<h', f.read(2))[0]

def read_long(f):
    return unpack('<q', f.read(8))[0]

def read_guid(f):
    # Only the first three fields seem to be stored in little-endian
    fields = (f.read(4)[::-1], f.read(2)[::-1], f.read(2)[::-1], f.read(2), f.read(6))
    if fields == ('\x00'*4, '\x00'*2, '\x00'*2, '\x00'*2, '\x00'*6):
        return None
    return "%s-%s-%s-%s-%s" % tuple(map(lambda s: s.encode('hex'), fields))


def parse_vdi_header(f):
    """Based on format description here:
    http://forums.virtualbox.org/viewtopic.php?t=8046
    """
    vdi = VDIHeader()

    # Header
    if f.read(33) != '<<< Sun VirtualBox Disk Image >>>':
        raise VDIError('not a vdi file')

    # Seems like reserved space
    f.seek(f.tell()+31)

    # signature
    if f.read(4) != '\x7f\x10\xda\xbe':
        raise VDIError('invalid signature')

    # Version
    vdi.version_minor, vdi.version_major = read_short(f), read_short(f)

    # Size of header (0x190)
    if read_int(f) != 0x190:
        raise VDIError('unexpected header size')

    # Image type
    vdi.type = read_int(f)

    # Flags
    vdi.flags = read_int(f)

    # Description (TODO: skip for now)
    f.seek(f.tell()+256)

    # offsetBlocks
    read_int(f)
    # offsetData
    read_int(f)
    # Number of cylinders
    if read_int(f) != 0:
        raise VDIError('unexpected cylinder count')
    # Number of heads
    if read_int(f) != 0:
        raise VDIError('unexpected head count')
    # Number of sectors
    if read_int(f) != 0:
        raise VDIError('unexpected sector count')
    # Sector size
    if read_int(f) != 512:
        raise VDIError('unexpected sector size')

    # Unused
    read_int(f)

    # Disk Size (in bytes)
    vdi.size = read_long(f)

    # Block Size
    vdi.block_size = read_int(f)
    # Block Extra Data
    if read_int(f) != 0:
        raise VDIError('unexpected block extra data')

    # Total number of blocks
    vdi.num_blocks = read_int(f)
    # Number of allocated blocks
    vdi.num_blocks_allocated = read_int(f)

    # uuid of disk
    vdi.uuid = read_guid(f)
    # uuid of last snapshot
    vdi.snapshot_uuid = read_guid(f)
    # uuid of parent
    vdi.parent_uuid = read_guid(f)

    return vdi


def read_vdis(filenames):
    """Read the headers of a list of VDI images.
    """
    vdis = {}
    for filename in filenames:
        if path.isdir(filename):
            log.error('%s: is a directory', filename)
            continue

        f = open(filename, 'r')
        try:
            vdi = parse_vdi_header(f)
        except VDIError:
            log.error("%s: not a vdi file", filename)
            continue

        if vdi.version_str != '1.1':
            log.error("%s: only version 1.1. is supported, this is %s", filename, vdi.version_str)
            continue

        if not vdi.type in (1, 2, 4):
            # All that is needed to support other types is finding the correct id mappings,
            # then generationg the proper xml format="" attribute.
            log.error("%s: Unsupported image type" % filename)
            continue

        vdis[filename] = vdi
    return vdis


class VDI(object):
    """Used to build a tree.
    """
    def __init__(self, filename, header, uuid=None, children=None):
        self.filename = filename
        self.h = self.header = header
        self.children = children or []
        self._uuid = uuid

    @property
    def uuid(self):
        return self._uuid if self._uuid else self.h.uuid


def construct_tree(vdis):
    """Take a list of VDIs, try to build a tree.
    """
    vdis = [VDI(filename, vdi) for filename, vdi in vdis.items()]
    non_root = []
    for current in vdis:
       for candidate in vdis:
          if current == candidate:
              continue
          if current.header.parent_uuid == candidate.header.uuid:
              non_root.append(current)
              candidate.children.append(current)
    tree = [v for v in vdis if not v in non_root]
    # Some VDIs may refer to a parent that we were not able to find. Construct
    # a special not found VDI record as their parent node.
    tree = [rn if rn.h.parent_uuid is None else VDI(None, None, uuid=rn.h.parent_uuid, children=[rn]) for rn in tree]
    return tree


def walk_tree(tree, func, start=0, indentation=' '*2):
    """Call ``func`` for every node in the tree.

    ``func`` takes (node, level) and should return (before, after).
    """
    def handle_node(node, level):
        def _print(what):
            if what:
                for line in what if isinstance(what, list) else [what]:
                    print "%s%s" % (indentation*level, line)

        before, after = func(node)
        _print(before)
        for c in node.children:
            handle_node(c, level+1)
        _print(after)
    for root in tree:
        handle_node(root, start)


def print_info(tree, detailed=False):
    """Print VDI info in a format more easily readable than XML.
    """
    if len(tree) == 1 and not tree[0].children:
        # If there is only a single node, always use detail mode
        detailed = True

    def p(node):
        filename = node.filename or '(not found)'
        if not detailed:
            start = '%s [UUID: %s]' % (filename, node.uuid)
        else:
            start = ['- %s' % node.uuid]
            start.append('  '+'-'*len(node.uuid))
            start.append('  Filename: %s' % filename)
            if node.h:
                start.append('  Type: %s' % VDI_TYPES.get(node.h.type, '??'))
                start.append('  Last snapshot: %s' % node.h.snapshot_uuid)
                start.append('  Size: %s bytes' % node.h.size)
            start.append('')

        return start, None
    walk_tree(tree, p, start=0, indentation=' '*4)


def print_diskmgmt_xml(tree):
    """Print the XML for use in the VirtualBox.xml file.
    """
    print "<MediaRegistry>"
    def p(node):
        open_tag = '<HardDisk uuid="%s" location="%s" format="VDI">' % (node.uuid, node.filename or '(not found)')
        return open_tag, "</HardDisk>"
    walk_tree(tree, p, start=1)
    print "</MediaRegistry>"


def parse_args(argv):
    parser = optparse.OptionParser(usage='%prog [options] filenames...')
    parser.add_option('--detail', help='print detailed VDI header info', action='store_true')
    parser.add_option('--xml', help='print XML to use in VirtualBox.xml file', action='store_true')
    options, filenames = parser.parse_args(argv)
    if not filenames:
        parser.print_help()
        sys.exit(1)
    return options, filenames


def main(argv):
    options, filenames = parse_args(argv)
    vdi_tree = construct_tree(read_vdis(filenames))

    if options.xml:
        print_diskmgmt_xml(vdi_tree)
    else:
        print_info(vdi_tree, detailed=options.detail)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]) or 0)
