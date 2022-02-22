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


st.set_page_config(page_title="EqualStreetNames - TODO", layout="wide", menu_items=None)
st.title('EqualStreetNames - TODO')

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


# select a city
cities = {
    'zurich': 'Zürich',
    'winterthur': 'Winterthur',
}
selected_city = st.selectbox(
    'Select a city',
    cities.keys(),
    index=0,
    format_func=lambda x: cities[x],
)

filtered_df = load_data(selected_city).copy()


filtered_df['osm_link'] = filtered_df.apply(osm_link, axis=1)
filtered_df['wikidata_link'] = filtered_df.apply(wikidata_link, axis=1)
filtered_df['named_after_link'] = filtered_df.apply(wikidata_link, args=('named_after',), axis=1)
filtered_df['name_ety_link'] = filtered_df.apply(wikidata_link, args=('name:etymology:wikidata',), axis=1)


# display content
st.header(f"Streets potential named after a person")
empty_name_ety = st.checkbox("Only display empty 'name:etymology:wikidata'", value=True)
empty_named_after = st.checkbox("Only display empty 'named_after'", value=True)
group_by_street = st.checkbox("Group by street", value=True)

if empty_name_ety:
    filtered_df = filtered_df.drop(filtered_df[filtered_df['name:etymology:wikidata'].notna()].index).reset_index(drop=True)

if empty_named_after:
    filtered_df = filtered_df.drop(filtered_df[filtered_df['named_after'].notna()].index).reset_index(drop=True)

if group_by_street:
    filtered_df = filtered_df.copy()
    filtered_df = filtered_df.groupby(['name', 'erlaeutertung', 'wikidata_link', 'named_after_link', 'name_ety_link'], as_index=False).count()
    st.write(filtered_df[['name', 'erlaeutertung', 'wikidata_link', 'named_after_link', 'name_ety_link']].to_html(escape=False), unsafe_allow_html=True)
else:
    st.write(filtered_df[['name', 'erlaeutertung', 'wikidata_link', 'named_after_link', 'osm_link', 'name_ety_link']].to_html(escape=False), unsafe_allow_html=True)

st.markdown('&copy; 2022 Stefan Oderbolz | [Github Repository](https://github.com/metaodi/equalstreetnames-todo)')
