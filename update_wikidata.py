#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Update wikidata with named-after claims

Usage:
  update_wikidata.py [--street <q-number> --named-after <q-number> | --file <data-file>]
  update_wikidata.py (-h | --help)
  update_wikidata.py --version

Options:
  -h, --help                   Show this screen.
  --version                    Show version.
  -s, --street <q-number>      Q-Number of street.
  -n, --named-after <q-number> Q-Number of named after.
  -f, --file <data-file>       Path to the CSV file [default: data.pkl].
"""

import sys
import os
import time
import copy
import json
from pprint import pprint

import pandas as pd
import requests
from docopt import docopt

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
arguments = docopt(__doc__, version='update_wikidata.py 1.0')

WIKIDATA_API_URL = 'https://www.wikidata.org/w/api.php'

# create a new Bot user here: https://www.wikidata.org/wiki/Special:BotPasswords

def login_to_wikidata():
    # Note: the login is saved in the requests session (i.e. in the cookies)
    #       so make sure to use the same session for all subsequent calls
    session = requests.Session()
    res = session.get(WIKIDATA_API_URL, params={
	'action': 'query',
	'meta': 'tokens',
	'type': 'login',
	'format': 'json',
    })
    res.raise_for_status()
    tokens = res.json()['query']['tokens']

    res = session.post(WIKIDATA_API_URL, data={
	'action': 'login',
	'lgname': os.getenv('WIKIDATA_USER'),
	'lgpassword': os.getenv('WIKIDATA_PASS'),
	'lgtoken': tokens['logintoken'],
	'format': 'json'
    })
    res.raise_for_status()
    login = res.json()
    return session

def csrf_of_wikidata(session):
    # generate csrf token
    res = session.get(WIKIDATA_API_URL, params={
	'action': 'query',
	'meta': 'tokens',
	'type': 'csrf',
	'format': 'json',
    })
    res.raise_for_status()
    csrf = res.json()['query']['tokens']['csrftoken']
    return csrf

def update_wikidata(row, session, interactive=True):
    # check if street has already a 'named after' claim
    street = wikidata_item(row['wikidata'])
    if 'P138' in street['claims']:
        print(f"Already found a 'named after' claim on {street['labels']['de']['value']} ({row['wikidata']}), continue")
        return

    if interactive:
        s = input(f"Enter Q-number for named after of {row['name']} ({row['wikidata']}), 's' to skip or 'q' to quit: ")
        if s.strip().lower() == 's':
            return
        if s.strip().lower() == 'q':
            sys.exit(0)

        named_after_id = int(s.lstrip('Q'))
    else:
        named_after_id = int(row['named_after'].lstrip('Q'))

    # find correct ID for named_after
    # add triple to stret
    item = row['wikidata']
    csrf = csrf_of_wikidata(session)
    data ={"entity-type": "item", "numeric-id": named_after_id}
    res = session.post(WIKIDATA_API_URL, data={
	'action': 'wbcreateclaim',
	'entity': item,
	'token': csrf,
	'snaktype': 'value',
	'property': 'P138',
	'value': json.dumps(data),
	'format': 'json',
    })
    res.raise_for_status()
    named_after = res.json()

    # add reference to strret name directory of Zurich
    csrf = csrf_of_wikidata(session)
    snaks = {
        'P248': [
            {
                "snaktype": 'value',
                "property": 'P248',
                "datavalue": {
                    "type": "wikibase-entityid",
                    "value": {
                        "entity-type": "item",
                        "numeric-id": 27320908,
                    }
                }
            },
        ]
    }
    res = session.post(WIKIDATA_API_URL, data={
        'action': 'wbsetreference',
        'statement': named_after['claim']['id'],
        'token': csrf,
        'snaks': json.dumps(snaks),
        'format': 'json',
    })
    print(res)
    res.raise_for_status()
    ref = res.json()
    
    if interactive:
        input(f"Update done: https://wikidata.org/wiki/{row['wikidata']}, press Enter to continue")
    else:
        print(f"Update done: https://wikidata.org/wiki/{row['wikidata']}")

def wikidata_item(item, endpoint='https://www.wikidata.org/w/api.php'):
    res = requests.get(endpoint, params={
        'action': 'wbgetentities',
        'ids': item,
        'format': 'json',
    })
    res.raise_for_status()
    response = res.json()
    # throttle requests
    time.sleep(0.1)
    return response.get('entities', {item: {}})[item]

session = login_to_wikidata()

path = arguments['--file']
street = arguments['--street']
named_after = arguments['--named-after']

if street and named_after:
    row = {'wikidata': street, 'named_after': named_after}
    update_wikidata(row, session, interactive=False)
else:
    filtered_df = pd.read_pickle(path)
    filtered_df = filtered_df.copy()
    filtered_df = filtered_df.groupby(['name', 'wikidata'], as_index=False).count()

    filtered_df.apply(update_wikidata, args=(session,), axis=1)
