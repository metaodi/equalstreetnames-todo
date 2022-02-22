# equalstreetnames-todo

Streamlit application running on heroku: https://equalstreetnames-todo.herokuapp.com/

EqualStreetNames Zurich: https://zurich.equalstreetnames.eu/ | https://github.com/EqualStreetNames/equalstreetnames-zurich
EqualStreetNames Winterthur: https://winterthur.equalstreetnames.eu/ | https://github.com/EqualStreetNames/equalstreetnames-winterthur

[![Screenshot](https://user-images.githubusercontent.com/538415/155046103-13afeb39-e46b-4c0b-b628-82b6acfa11ac.png)](https://equalstreetnames-todo.herokuapp.com/)


The basic idea is to show streets from OpenStreetMap combined with data from the official Strassennamenverzeichnis and WikiData.
Ideally new links on WikiData are created (e.g. add a "named after" claim to a street).

To load the data. a github action is run regularly and the data uploaded as artifact.
These arrifacts are then downloaded to heroku.


# Scripts

## `fetch_data.py`

Script to load and combine the data from the Strassenverzeichnis (provided by Open Data Zurich), OpenStreetMap (via Overpass) and Wikidata.
At the end of this script a file called `data.pkl` is generated, which is then used by the other scripts to load its data.

## `download_data_from_github.py`

The fetch_data.py script above is run on GitHub Actions on a regular basis.
This download script allows to download the `data.pkl` from the latest run on GitHub instead of generated the file itself.

## `update_osm.py`

Script to apply the `named after` claims from Wikidata as `name:etymology:wikidata` tags to OpenStreetMap.

## `update_wikidata.py`

Script to easily add 'named after' claims to Wikidata based on the user input.
