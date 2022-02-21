#!/usr/bin/env python
# coding: utf-8
"""Download latest data.pkl from GitHub Actions

Usage:
  download_data_from_github.py
  download_data_from_github.py (-h | --help)
  download_data_from_github.py --version

Options:
  -h, --help                   Show this screen.
  --version                    Show version.
"""

import os
import io
import zipfile

import pandas as pd
from docopt import docopt
from ghapi.all import GhApi
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
arguments = docopt(__doc__, version='download_data_from_github.py 1.0')


# read data.pkl from GitHub Actions Artifacts
github_token = os.environ['GITHUB_TOKEN']
owner = os.getenv('GITHUB_REPO_OWNER', 'metaodi')
repo = os.getenv('GITHUB_REPO', 'equalstreetnames-todo')
api = GhApi(owner=owner, repo=repo, token=github_token)
artifacts = api.actions.list_artifacts_for_repo()['artifacts']
download = api.actions.download_artifact(artifact_id=artifacts[0]['id'], archive_format="zip")

with zipfile.ZipFile(io.BytesIO(download)) as zip_ref:
    zip_ref.extractall('.')

df = pd.read_pickle("data.pkl")
print(df[['name', 'wikidata', 'id', 'type']])

