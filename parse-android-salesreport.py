#!/usr/bin/env python
import csv, itertools, sys, locale
from decimal import Decimal


def read_csv(file):
    with open(file, 'r') as f:
        return list(csv.DictReader(f, delimiter=','))


def group_by(records, key):
    # itertools.groupby requires sorted input
    records.sort(key=key)
    
    result = {}
    for country, sales in itertools.groupby(records, key=key):
        charged = lambda s: Decimal(locale.atof(s['Charged Amount']))
        fx = lambda s: Decimal(locale.atof(s['Estimated FX Rate'] or '1'))
        result[country] = sum([charged(s) * fx(s) for s in sales])
        #result[country] = len(list(sales))
        
    return result
                         
                         
if __name__ == '__main__':
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    
    # define different keys
    country = lambda x: x['Country of Buyer']
    eu_codes = ['AT', 'BE', 'BG', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'EL', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE']
    euvat = lambda x: 'EU' if x['Country of Buyer'] in eu_codes else 'Non-EU'
    
    records = read_csv(sys.argv[1])
    for country, income in sorted(group_by(records, euvat).items(), key=lambda t: t[1]):
        print country, income, Decimal('0.19') * income
