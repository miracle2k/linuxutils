#!/usr/bin/env python
# coding: utf8
import csv, itertools, sys, os, locale, operator, collections
from decimal import Decimal
import texttable    # pip install texttable


class CommentedFile(object):
    """The new montyly payout reports available since 2012 now have comments
    in them. The older "sales reports" did not.

    http://bugs.python.org/msg48505"""
    def __init__(self, f, commentstring="#"):
        self.f = f
        self.commentstring = commentstring
    def next(self):
        line = self.f.next()
        while line.startswith(self.commentstring):
            line = self.f.next()
        return line
    def __iter__(self):
        return self


def read_csv(file):
    with open(file, 'r') as f:
        return list(csv.DictReader(CommentedFile(f), delimiter=','))


def group_by(records, key):
    # itertools.groupby requires sorted input
    records.sort(key=key)
    
    result = collections.OrderedDict()
    for country, sales in itertools.groupby(records, key=key):
        sales = list(sales)
        charged = lambda s: Decimal(str(locale.atof(s['Charged Amount'])))
        received = lambda s: Decimal(str(locale.atof(s['Merchant Receives'])))
        fx = lambda s: Decimal(str(locale.atof(s['Estimated FX Rate'] or '1')))
        result[country] = {
          'charged': sum([charged(s) * fx(s) for s in sales]),
          'received': sum([received(s) for s in sales]),
          'num_sales': len(list(sales)),
        }
    result['SUM'] = reduce(operator.add, map(collections.Counter, result.values()))
        
    return result
                         
                         
if __name__ == '__main__':
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    
    # define different keys
    country = lambda x: x['Country of Buyer']
    eu_codes = ['AT', 'BE', 'BG', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'EL', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE']
    euvat = lambda x: 'EU' if x['Country of Buyer'] in eu_codes else 'Non-EU'
    
    for filename in sorted(sys.argv[1:]):
        table = texttable.Texttable()
        #table.set_deco(texttable.Texttable.HEADER)
        table.set_cols_dtype(['t', 'i', 't', 't', 't', 't'])
        table.set_cols_align(["l", 'r', "r", "r", "r", "r"])
        table.header(['', 'Num', 'Charged', '19%', 'Received', '19%'])

        print os.path.basename(filename)
        records = read_csv(filename)
        for country, data in sorted(group_by(records, euvat).items(), key=lambda t: t[1]):
            table.add_row([
                country,
                data['num_sales'],
                '%.2f €' % data['charged'],
                '%.2f €' % (Decimal('0.19') * data['charged']),
                '%.2f €' % data['received'],
                '%.2f €' % (Decimal('0.19') * data['received']),
            ])

        # Indent table by 4 spaces
        print 4 * ' ' + table.draw().replace('\n', '\n' + (4 * ' '))
