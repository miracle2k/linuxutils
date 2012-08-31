#!/usr/bin/python
"""
From: http://code.activestate.com/recipes/576587-sort-sections-and-keys-in-ini-file/
Original Author: Michal Niklas
"""

import sys

USAGE = 'USAGE:\n\tinisort.py file.ini'

def sort_ini(stream):
	"""sort .ini file: sorts sections and in each section sorts keys"""
	lines = stream.readlines()
	section = ''
	sections = {}
	for line in lines:
		line = line.strip()
		if line:
			if line.startswith('['):
				section = line
				continue
			if section:
				try:
					sections[section].append(line)
				except KeyError:
					sections[section] = [line, ]
	if sections:
		sk = sections.keys()
		sk.sort()
		for k in sk:
			vals = sections[k]
			vals.sort()
			print k
			print '\n'.join(vals)
			print


def main():
    if '-h' in sys.argv or '--help' in sys.argv or len(sys.argv) > 2:
	    print USAGE
    else:
        if len(sys.argv) == 2:
            with open(sys.argv[1]) as f:
                sort_ini(f)
        else:
            sort_ini(sys.stdin)


if __name__ == '__main__':
     sys.exit(main() or 0)
