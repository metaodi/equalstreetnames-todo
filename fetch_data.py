#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch data from Strassenverzeichnis, Overpass and WikiData

Usage:
  fetch_data.py [-c <city>]
  fetch_data.py (-h | --help)
  fetch_data.py --version

Options:
  -h, --help                   Show this screen.
  --version                    Show version.
  -c, --city <city>            Download data for the city [default: zurich].
"""

import os
import json
import time
from pprint import pprint

from docopt import docopt
import requests
import geopandas
import pandas as pd
import xml.etree.ElementTree as ET
import osm2geojson
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
arguments = docopt(__doc__, version='fetch_data.py 1.0')


def overpass_query(q, endpoint='http://overpass.osm.ch/api/interpreter'):
    r = requests.get(endpoint, params={'data': q})
    r.raise_for_status()
    osm_gj = osm2geojson.json2geojson(r.json())
    for f in osm_gj['features']:
        props = {}
        for p, v in f['properties'].items():
            if isinstance(v, dict):
                for ip, iv in v.items():
                    props[ip] = iv
            else:
                props[p] = v
        f['properties'] = props
    return osm_gj

def wikidata_item(item, endpoint='https://www.wikidata.org/w/api.php'):
    res = requests.get(endpoint, params={
        'action': 'wbgetentities',
        'ids': item,
        'format': 'json',
    })
    response = res.json()
    print(response)
    # throttle requests
    time.sleep(0.1)
    return response.get('entities', {item: {}})[item]

def load_wfs_data(wfs_url, layer):
    r = requests.get(wfs_url, params={
        'service': 'WFS',
        'version': '1.0.0',
        'request': 'GetFeature',
        'typename': layer,
        'outputFormat': 'GeoJSON'
    })
    str_verz_geo = r.json()
    return str_verz_geo

def named_after(row):
    if not row['wikidata'] or pd.isna(row['wikidata']):
        return None
    print(f"Fetch `named after` of {row['wikidata']}")
    wd_item = wikidata_item(row['wikidata'])
    if 'P138' not in wd_item.get('claims', {}):
        return None
    print(wd_item['claims']['P138'][0]['mainsnak'])
    named_id = wd_item['claims']['P138'][0]['mainsnak']['datavalue']['value']['id']
    return named_id

load_dotenv(find_dotenv())
user = os.getenv('OSM_USER')
pw = os.getenv('OSM_PASS')
city = arguments['--city']

lv95 = 'EPSG:2056'
wgs84 = 'EPSG:4326'

if city == 'zurich':
    str_verz_layer = 'sv_str_verz'
    wfs_url = 'https://www.ogd.stadt-zuerich.ch/wfs/geoportal/Strassennamenverzeichnis' 
    # load data from WFS
    str_verz_geo = load_wfs_data(wfs_url, str_verz_layer)

    str_verz = [{'strassenname': f['properties']['str_name'], 'erlaeuterung': f['properties']['snb_erlaeuterung']} for f in str_verz_geo['features']]
    df_str = pd.DataFrame.from_dict(str_verz)

if city == 'basel':
    df_bs_str = pd.read_csv('https://data.bs.ch/explore/dataset/100189/download/?format=csv&timezone=Europe/Zurich&lang=en&use_labels_for_header=true&csv_separator=,')
    df_bs_str['erlaeuterung'] = df_bs_str[['Erklärung erste Zeile', 'Erklärung zweite Zeile']].apply(lambda x: '\n'.join(x.dropna()), axis=1)

# load data from OSM via Overpass
q_map = {
    'zurich': 'Q72',
    'winterthur': 'Q9125',
    'basel': 'Q78',
}
city_q = q_map[city]

streets_query = f"""
[out:json][timeout:300];
( area["admin_level"=""]["wikidata"="{city_q}"]; )->.a;
(
    way["highway"]["name"]["highway"!="bus_stop"]["highway"!="elevator"]["highway"!="platform"](area.a);
    way["place"="square"]["name"](area.a);
);
out body;
>;
out skel qt;
"""
osm_result = overpass_query(streets_query)
osm_df = geopandas.GeoDataFrame.from_features(osm_result, crs=wgs84)

# Join OSM data with Strassenverzeichnis
if city == 'zurich':
    merged_df = osm_df.merge(df_str, how="left", left_on='name', right_on='Strassenname')
    filtered_df = merged_df[merged_df['erlaeuterung'].str.match(r'^(.+\(\d{4}-\d{4}\)|.*Vorname)')==True].reset_index(drop=True)
elif city == 'basel':
    merged_df = osm_df.merge(df_bs_str, how="left", left_on='name', right_on='Strassenname')
    filtered_df = merged_df.copy()
else:
    filtered_df = osm_df.copy()

# filter auf alle die Personen sein könnten: Einträge in der Form «Vorname Name (Jahr-Jahr)»
filtered_df['named_after'] = filtered_df.apply(named_after, axis=1)
filtered_df = filtered_df.copy()
filtered_df.to_pickle(f'data-{city}.pkl')
