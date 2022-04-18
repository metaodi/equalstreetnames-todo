#!/usr/bin/env python
# coding: utf-8

import streamlit as st

import os
import json
import time
from pprint import pprint
import io
import zipfile

import requests
import geopandas
import pandas as pd
import xml.etree.ElementTree as ET
import osm2geojson
from ghapi.all import GhApi
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


st.set_page_config(page_title="EqualStreetNames - TODO", menu_items=None)
st.title('EqualStreetNames - TODO')

query_params = st.experimental_get_query_params()
city = query_params.get('city', ['zurich'])[0]

# select a city
cities = {
    'zurich': 'Zürich',
    'basel': 'Basel',
    'winterthur': 'Winterthur',
}
options = list(cities.keys())
selected_city = st.sidebar.selectbox(
    'Select a city',
    cities.keys(),
    index=options.index(city),
    format_func=lambda x: cities[x],
)
st.experimental_set_query_params(city=selected_city)

# add options to sidebar
empty_name_ety = st.sidebar.checkbox("Only display empty 'name:etymology:wikidata'", value=False)
empty_named_after = st.sidebar.checkbox("Only display empty 'named_after'", value=False)
empty_wikidata_link = st.sidebar.checkbox("Only display empty 'wikidata_link'", value=False)
group_by_street = st.sidebar.checkbox("Group by street", value=True)

@st.cache(ttl=900)
def load_data(city='zurich'):
    # read data.pkl from GitHub Actions Artifacts
    github_token = os.environ['GITHUB_TOKEN']
    owner = os.getenv('GITHUB_REPO_OWNER', 'metaodi')
    repo = os.getenv('GITHUB_REPO', 'equalstreetnames-todo')

    api = GhApi(owner=owner, repo=repo, token=github_token)
    artifacts = api.actions.list_artifacts_for_repo()['artifacts']
    latest_artificat = next(filter(lambda x: x['name'] == city, artifacts), {})
    download = api.actions.download_artifact(artifact_id=latest_artificat['id'], archive_format="zip")

    with zipfile.ZipFile(io.BytesIO(download)) as zip_ref:
        zip_ref.extractall('.')

    df = pd.read_pickle(f"data-{city}.pkl")
    return df

def osm_link(r):
    return f"<a href='https://openstreetmap.org/{r['type']}/{r['id']}'>{r['type']}/{r['id']}</a>"

def wikidata_link(r, attr='wikidata'):
    if attr not in r or not r[attr] or pd.isna(r[attr]):
        return ''
    return f"<a href='https://www.wikidata.org/wiki/{r[attr]}'>{r[attr]}</a>"


filtered_df = load_data(selected_city).copy()

filtered_df['osm_link'] = filtered_df.apply(osm_link, axis=1)
filtered_df['wikidata_link'] = filtered_df.apply(wikidata_link, axis=1)
filtered_df['named_after_link'] = filtered_df.apply(wikidata_link, args=('named_after',), axis=1)
filtered_df['name_ety_link'] = filtered_df.apply(wikidata_link, args=('name:etymology:wikidata',), axis=1)


# display content
st.header(f"Streets potential named after a person")

if empty_name_ety and 'name:etymology:wikidata' in filtered_df:
    filtered_df = filtered_df.drop(filtered_df[filtered_df['name:etymology:wikidata'].notna()].index).reset_index(drop=True)

if empty_named_after:
    filtered_df = filtered_df.drop(filtered_df[filtered_df['named_after'].notna()].index).reset_index(drop=True)

if empty_wikidata_link:
    filtered_df = filtered_df.drop(filtered_df[filtered_df['wikidata'].notna()].index).reset_index(drop=True)

if group_by_street and 'erlaeuterung' in filtered_df:
    filtered_df = filtered_df.copy()
    filtered_df = filtered_df.groupby(['name', 'erlaeuterung', 'wikidata_link', 'named_after_link', 'name_ety_link'], as_index=False).count()
    st.write(filtered_df[['name', 'erlaeuterung', 'wikidata_link', 'named_after_link', 'name_ety_link']].to_html(escape=False), unsafe_allow_html=True)
elif group_by_street:
    filtered_df = filtered_df.groupby(['name', 'wikidata_link', 'named_after_link', 'name_ety_link'], as_index=False).count()
    st.write(filtered_df[['name', 'wikidata_link', 'named_after_link', 'name_ety_link']].to_html(escape=False), unsafe_allow_html=True)
elif 'erlaeuterung' in filtered_df:
    st.write(filtered_df[['name', 'erlaeuterung', 'wikidata_link', 'named_after_link', 'osm_link', 'name_ety_link']].to_html(escape=False), unsafe_allow_html=True)
else:
    st.write(filtered_df[['name', 'wikidata_link', 'named_after_link', 'osm_link', 'name_ety_link']].to_html(escape=False), unsafe_allow_html=True)

st.markdown('&copy; 2022 Stefan Oderbolz | [Github Repository](https://github.com/metaodi/equalstreetnames-todo)')
