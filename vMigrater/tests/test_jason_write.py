#!/usr/bin/python

import json

data = {}  
data['people'] = []  
data['people'].append({
    'name': 'Scott1',
    'website': 'stackabuse1.com',
    'from': 'Nebraska1'
})
data['people'].append({
    'name': 'Larry2',
    'website': 'google2.com',
    'from': 'Michigan2'
})
with open('data.txt', 'w') as outfile:
    json.dump(data, outfile)

