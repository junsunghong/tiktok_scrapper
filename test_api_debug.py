import streamlit as st
import pandas as pd
from real_data_fetcher import RealDataFetcher
import toml
import os

# Load secrets directly
try:
    secrets = toml.load(".streamlit/secrets.toml")
    api_key = secrets["general"]["rapidapi_key"]
    print(f"Loaded API Key: {api_key[:5]}...")
except Exception as e:
    print(f"Error loading secrets: {e}")
    exit(1)

fetcher = RealDataFetcher(api_key)
print("Fetching #SaaS posts (Limit 10, Sort 0)...")
df = fetcher.fetch_posts("#SaaS", limit=10, sort_type=0)

if df.empty:
    print("DataFrame is empty.")
else:
    print(f"Fetched {len(df)} posts.")
    print(df[['title', 'viral_score', 'date']].head())
