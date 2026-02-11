import streamlit as st
import pandas as pd
from data_fetcher import MockDataFetcher

# Layout Configuration
st.set_page_config(page_title="Viral UGC Discovery", page_icon="🚀", layout="wide")

# Custom CSS for "Yorby-like" card view
st.markdown("""
<style>
    .card {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
        border: 1px solid #333;
    }
    .metric-container {
        display: flex;
        justify-content: space-between;
        margin-top: 10px;
        font-size: 0.9em;
        color: #CCC;
    }
    .badge {
        background-color: #FF4B4B;
        color: white;
        padding: 2px 8px;
        border-radius: 5px;
        font-size: 0.8em;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# Sidebar Filters
with st.sidebar:
    st.header("🔑 API Configuration")
    
    # Try to load from secrets
    try:
        api_key = st.secrets["general"]["rapidapi_key"]
        st.success("API Key loaded from secrets ✨")
    except FileNotFoundError:
        api_key = st.text_input("RapidAPI Key (TikAPI)", type="password", help="Get key from rapidapi.com/tikwm-tikwm-default/api/tiktok-scraper7")
    except KeyError:
        api_key = st.text_input("RapidAPI Key (TikAPI)", type="password", help="Get key from rapidapi.com/tikwm-tikwm-default/api/tiktok-scraper7")
    
    st.header("🔍 Filters")
    selected_hashtag = st.text_input("Niche / Hashtag", value="#SaaS", help="Enter any hashtag (e.g. #AI, #Marketing, #Crypto)")
    if not selected_hashtag.startswith("#"):
        selected_hashtag = f"#{selected_hashtag}"
    min_viral_score = st.slider("Minimum Viral Score (Views/Followers)", 0.0, 50.0, 5.0)
    st.info(f"Showing posts with > {min_viral_score}x more views than followers.")

# Title & Description (Dynamic)
st.title("🚀 Viral Organic UGC Database (Prototype)")
st.markdown(f"Discover high-performing content in the <span style='color: #00FF99; font-weight: bold;'>{selected_hashtag}</span> niche before it peaks.", unsafe_allow_html=True)

# Data Fetching
@st.cache_data(ttl=3600)
def load_data(hashtag, key):
    if key:
        from real_data_fetcher import RealDataFetcher
        fetcher = RealDataFetcher(key)
        try:
            data = fetcher.fetch_posts(hashtag, limit=30)
            if not data.empty:
                return data, "Real API", "Success"
            else:
                return pd.DataFrame(), "Real API", "No Data"
        except Exception as e:
            return pd.DataFrame(), "Real API", str(e)
            
    # Fallback or Mock
    fetcher = MockDataFetcher()
    return fetcher.fetch_posts(hashtag, limit=30), "Mock Data", "Success"

df, source_label, status_msg = load_data(selected_hashtag, api_key)

if status_msg == "Success":
    if source_label == "Real API":
        st.toast(f"✅ Loaded {len(df)} items from Real API!", icon="📡")
    else:
        st.toast("Using Mock Data", icon="🤖")
elif status_msg == "No Data":
    st.toast("⚠️ Real API returned no data. Check API Key or Hashtag.", icon="❌")
else:
    st.error(f"API Error: {status_msg}")

# DEBUG: Inspect Raw Data
with st.expander("Debug: Raw Data Inspection"):
    if not df.empty:
        st.write("First Row Data:")
        st.json(df.iloc[0].to_dict())


# Display Data Source Status
st.caption(f"Data Source: **{source_label}**")

# Filtering Logic
if not df.empty and 'viral_score' in df.columns:
    filtered_df = df[df['viral_score'] >= min_viral_score].sort_values(by='viral_score', ascending=False)
else:
    filtered_df = pd.DataFrame()

# Display Stats
col1, col2, col3 = st.columns(3)
col1.metric("Total Posts Scanned", len(df))
col2.metric("Viral Hidden Gems Found", len(filtered_df))

if not filtered_df.empty:
    top_score = filtered_df['viral_score'].max()
else:
    top_score = 0

col3.metric("Top Viral Score", f"{top_score}x")

st.divider()

# Gallery View
if len(filtered_df) == 0:
    st.warning("No viral posts found with this filter. Try lowering the Viral Score.")
else:
    cols = st.columns(3) # Grid Layout
    for index, (i, row) in enumerate(filtered_df.iterrows()):
        with cols[index % 3]:
            # Simulate a Card UI
            # Clickable Image Card using Markdown
            # Use wsrv.nl proxy via real_data_fetcher or fallback
            thumbnail = row.get('thumbnail_url', "https://picsum.photos/400/600")
            link = row.get('video_url', "#")
            
            st.markdown(f"""
            <a href="{link}" target="_blank">
                <img src="{thumbnail}" style="width:100%; border-radius:10px; margin-bottom:10px;">
            </a>
            """, unsafe_allow_html=True)
            
            st.subheader(f"{row['virality_label']}")
            st.write(f"**[{row['title']}]({link})**")
            
            # Metrics
            st.write(f"👁️ **{row['views']:,}** Views")
            st.write(f"👤 **{row['followers']:,}** Followers")
            st.write(f"🔥 **Score: {row['viral_score']}x**")
            
            with st.expander("Analysis"):
                st.write(f"This post has **{row['viral_score']}x** more views than the author has followers, indicating high organic reach.")

