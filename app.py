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


# Initialize Session State
if 'active_hashtag' not in st.session_state:
    st.session_state.active_hashtag = None
if 'active_min_viral' not in st.session_state:
    st.session_state.active_min_viral = 5.0

# Sidebar Filters
with st.sidebar:
    st.header("🔑 API Configuration")
    
    # Try to load from secrets
    secrets_key = None
    try:
        secrets_key = st.secrets["general"]["rapidapi_key"]
        st.success("API Key loaded from secrets ✨")
    except (FileNotFoundError, KeyError):
        pass

    with st.form("search_form"):
        # API Key Input (if not in secrets)
        if not secrets_key:
            api_key_input = st.text_input("RapidAPI Key (TikAPI)", type="password", help="Get key from rapidapi.com/tikwm-tikwm-default/api/tiktok-scraper7")
        else:
            api_key_input = secrets_key
        
        st.header("🔍 Filters")
        hashtag_input = st.text_input("Niche / Hashtag", value="#SaaS", help="Enter any hashtag (e.g. #AI, #Marketing, #Crypto)")
        if not hashtag_input.startswith("#"):
            hashtag_input = f"#{hashtag_input}"
            
        viral_score_input = st.slider("Minimum Viral Score (Views/Followers)", 0.0, 50.0, 5.0)
        
        # Search Button
        search_submitted = st.form_submit_button("Search 🔎")
        
        if search_submitted:
            st.session_state.active_hashtag = hashtag_input
            st.session_state.active_min_viral = viral_score_input
            # If manual input is used, we might need to store it too, 
            # but usually we just pass it to load_data immediately if structure allows.
            # Here we just use the variable in the main flow? 
            # No, main flow runs outside form. We need session state.

    st.info(f"Showing posts with > {st.session_state.active_min_viral}x more views than followers.")

# Determine which key to use for fetching
final_api_key = secrets_key if secrets_key else api_key_input

# Title & Description (Dynamic)
st.title("🚀 Viral Organic UGC Database (Prototype)")
if st.session_state.active_hashtag:
    st.markdown(f"Discover high-performing content in the <span style='color: #00FF99; font-weight: bold;'>{st.session_state.active_hashtag}</span> niche before it peaks.", unsafe_allow_html=True)
else:
    st.markdown("Discover high-performing content in your niche before it peaks.")

# Main Execution Flow
if not st.session_state.active_hashtag:
    st.info("👈 Please enter a Hashtag and click **Search** in the sidebar to start!")
    st.stop()

# Data Fetching (Uses Session State Hashtag)
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

df, source_label, status_msg = load_data(st.session_state.active_hashtag, final_api_key)

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
    filtered_df = df[df['viral_score'] >= st.session_state.active_min_viral].sort_values(by='viral_score', ascending=False)
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

