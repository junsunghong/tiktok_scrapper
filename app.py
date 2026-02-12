import streamlit as st
import pandas as pd
from data_fetcher import MockDataFetcher
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# Authentication must come FIRST before any st. commands
# Load credentials from secrets
name = None
authentication_status = None
username = None
user_api_key = None
authenticator = None

try:
    # Build credentials dict from secrets - must manually convert since secrets is immutable
    credentials = {
        'cookie': {
            'name': st.secrets['credentials']['cookie']['name'],
            'key': st.secrets['credentials']['cookie']['key'],
            'expiry_days': st.secrets['credentials']['cookie']['expiry_days']
        },
        'usernames': {}
    }
    
    # Convert usernames
    for username_key in st.secrets['credentials']['usernames']:
        user_data = st.secrets['credentials']['usernames'][username_key]
        credentials['usernames'][username_key] = {
            'name': user_data['name'],
            'password': user_data['password'],
            'api_key': user_data['api_key']
        }
    
    # Create authenticator
    authenticator = stauth.Authenticate(
        credentials,
        st.secrets['credentials']['cookie']['name'],
        st.secrets['credentials']['cookie']['key'],
        int(st.secrets['credentials']['cookie']['expiry_days'])
    )
    
    # Render login widget - v0.4 API returns None, stores in st.session_state
    authenticator.login(location='sidebar')
    
    # Access authentication status from session state (v0.4 API)
    if 'authentication_status' in st.session_state:
        authentication_status = st.session_state['authentication_status']
        name = st.session_state.get('name')
        username = st.session_state.get('username')
    
    if authentication_status == False:
        st.error('Username/password is incorrect')
        st.stop()
    elif authentication_status == None:
        st.warning('Please enter your username and password')
        st.stop()
    
    # If authenticated, get the user's API key
    if authentication_status and username:
        user_api_key = credentials['usernames'][username]['api_key']
    
except (KeyError, Exception) as e:
    # Running without authentication (development mode or secrets not configured)
    st.warning(f"⚠️ Authentication Error: {str(e)}")
    st.info("Running without authentication (development mode)")
    
    # Try to get API key from old general section
    try:
        user_api_key = st.secrets["general"]["rapidapi_key"]
        st.success("✅ API Key loaded from general section")
    except Exception as e2:
        st.error(f"❌ Could not load API key: {str(e2)}")
        user_api_key = None

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
if 'platform' not in st.session_state:
    st.session_state.platform = 'TikTok'
if 'youtube_page_token' not in st.session_state:
    st.session_state.youtube_page_token = None
if 'youtube_prev_token' not in st.session_state:
    st.session_state.youtube_prev_token = None
if 'youtube_order' not in st.session_state:
    st.session_state.youtube_order = 'date'  # Default to recent uploads
if 'youtube_video_type' not in st.session_state:
    st.session_state.youtube_video_type = 'any'

# Sidebar Filters
with st.sidebar:
    # Show logged in user or dev mode
    if authentication_status:
        st.success(f"👤 Logged in as: **{name}**")
        if authenticator:
            authenticator.logout(location='sidebar')
    else:
        st.info("🔧 Development Mode (No Auth)")
        if not user_api_key:
            st.warning("⚠️ No API Key configured")
    
    st.divider()
    
    # Platform Selector
    st.header("📱 Platform")
    platform = st.selectbox(
        "Select Platform",
        options=['TikTok', 'YouTube'],
        index=0 if st.session_state.platform == 'TikTok' else 1,
        key='platform_selector'
    )
    
    if platform != st.session_state.platform:
        st.session_state.platform = platform
        st.rerun()
    
    st.divider()
    
    with st.form("search_form"):
        st.header("🔍 Filters")
        
        # Common settings based on platform
        if platform == 'TikTok':
            # TikTok Filters
            default_hashtag = st.session_state.active_hashtag if st.session_state.active_hashtag else "#SaaS"
            
            hashtag_input = st.text_input("Niche / Hashtag", value=default_hashtag, help="Enter any hashtag (e.g. #AI, #Marketing, #Crypto)")
            if not hashtag_input.startswith("#"):
                hashtag_input = f"#{hashtag_input}"
                
            # Simplified Inputs (Selectbox)
            viral_score_input = st.selectbox("Min Viral Score", [1, 3, 5], index=0)
            
            # Simplified Limit (Selectbox)
            search_limit = st.selectbox("Max Videos to Scan", [30, 50, 100], index=0)
            
            # Search Button
            search_submitted = st.form_submit_button("Search 🔎")
            
            if search_submitted:
                st.session_state.active_hashtag = hashtag_input
                st.session_state.active_min_viral = viral_score_input
                st.session_state.active_limit = search_limit
                st.rerun()
        
        else:  # YouTube
            # YouTube Filters
            default_query = st.session_state.active_hashtag if st.session_state.active_hashtag else "AI"
            
            query_input = st.text_input("Search Keywords", value=default_query, help="Enter keywords or hashtags (e.g. AI, #tech)")
            
            # Video Type
            video_type = st.selectbox(
                "Video Type",
                options=['All Videos', 'Shorts Only (<60s)', 'Long-form (≥60s)'],
                index=0
            )
            
            # Map to API parameter
            if video_type == 'Shorts Only (<60s)':
                video_duration = 'short'  # < 4 min (we'll filter < 60s in code)
            elif video_type == 'Long-form (≥60s)':
                video_duration = 'medium'  # Or 'long' - we'll include both
            else:
                video_duration = 'any'
            
            # Min Viral Score
            viral_score_input = st.selectbox("Min Viral Score", [1, 3, 5, 10], index=0)
            
            # Max Results
            max_results = st.selectbox("Results per Page", [10, 25, 50], index=1)
            
            # Search Button
            search_submitted = st.form_submit_button("Search 🔎")
            
            if search_submitted:
                st.session_state.active_hashtag = query_input
                st.session_state.active_min_viral = viral_score_input
                st.session_state.active_limit = max_results
                st.session_state.youtube_order = 'date'  # Always sort by recent uploads
                st.session_state.youtube_video_type = video_type
                st.session_state.youtube_page_token = None  # Reset pagination
                st.session_state.youtube_prev_token = None
                st.rerun()
    
    # Initialize new session state defaults if they don't exist
    if 'active_limit' not in st.session_state:
        st.session_state.active_limit = 30 if platform == 'TikTok' else 25

    st.success(f"✅ Filter: Score > {st.session_state.active_min_viral} | Limit: {st.session_state.active_limit}")

# Use authenticated user's API key
final_api_key = user_api_key

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
def load_tiktok_data(hashtag, key, limit):
    if key:
        from real_data_fetcher import RealDataFetcher
        fetcher = RealDataFetcher(key)
        try:
            # Always use Default Sort (0)
            data = fetcher.fetch_posts(hashtag, limit=limit, sort_type=0)
            if not data.empty:
                return data, "TikTok API", "Success"
            else:
                return pd.DataFrame(), "TikTok API", "No Data"
        except Exception as e:
            return pd.DataFrame(), "TikTok API", str(e)
            
    # Fallback or Mock
    fetcher = MockDataFetcher()
    return fetcher.fetch_posts(hashtag, limit=limit), "Mock Data", "Success"


@st.cache_data(ttl=3600)
def load_youtube_data(query, youtube_key, max_results, order, video_duration, page_token):
    """Load YouTube data with pagination support"""
    if not youtube_key:
        return pd.DataFrame(), None, None, "YouTube API", "No API Key"
    
    try:
        from youtube_fetcher import YouTubeDataFetcher
        fetcher = YouTubeDataFetcher(youtube_key)
        df, next_token, prev_token = fetcher.search_videos(
            query=query,
            max_results=max_results,
            order=order,
            video_duration=video_duration,
            page_token=page_token
        )
        
        if not df.empty:
            return df, next_token, prev_token, "YouTube API", "Success"
        else:
            return pd.DataFrame(), None, None, "YouTube API", "No Data"
    except Exception as e:
        return pd.DataFrame(), None, None, "YouTube API", str(e)


# Platform-specific data loading
if st.session_state.platform == 'TikTok':
    df, source_label, status_msg = load_tiktok_data(
        st.session_state.active_hashtag,
        final_api_key,
        st.session_state.active_limit
    )
    next_token = None
    prev_token = None
else:  # YouTube
    # Get YouTube API key from secrets
    try:
        youtube_key = st.secrets["general"]["youtube_api_key"]
    except:
        youtube_key = None
    
    # Determine video_duration from session state
    video_type_filter = st.session_state.get('youtube_video_type', 'All Videos')
    if 'Shorts' in video_type_filter:
        video_duration = 'short'
    elif 'Long-form' in video_type_filter:
        video_duration = 'medium'
    else:
        video_duration = 'any'
    
    df, next_token, prev_token, source_label, status_msg = load_youtube_data(
        st.session_state.active_hashtag,
        youtube_key,
        st.session_state.active_limit,
        st.session_state.get('youtube_order', 'relevance'),
        video_duration,
        st.session_state.get('youtube_page_token')
    )
    
    # Store tokens for pagination
    if next_token or prev_token:
        st.session_state.youtube_next_token = next_token
        st.session_state.youtube_prev_token = prev_token

# YouTube Pagination Controls
if st.session_state.platform == 'YouTube':
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        if st.button("◄ Previous Page") and st.session_state.get('youtube_prev_token'):
            st.session_state.youtube_page_token = st.session_state.youtube_prev_token
            st.rerun()
    
    with col3:
        if st.button("Next Page ►") and st.session_state.get('youtube_next_token'):
            st.session_state.youtube_page_token = st.session_state.youtube_next_token
            st.rerun()
    
    st.divider()

# Filter YouTube Shorts by actual 60s threshold
if st.session_state.platform == 'YouTube' and not df.empty:
    video_type_filter = st.session_state.get('youtube_video_type', 'All Videos')
    if 'Shorts' in video_type_filter and 'duration_seconds' in df.columns:
        df = df[df['duration_seconds'] < 60].copy()
    elif 'Long-form' in video_type_filter and 'duration_seconds' in df.columns:
        df = df[df['duration_seconds'] >= 60].copy()

if status_msg == "Success":
    if "API" in source_label:
        st.toast(f"✅ Loaded {len(df)} items from {source_label}!", icon="📡")
    else:
        st.toast("Using Mock Data", icon="🤖")
elif status_msg == "No Data":
    st.toast(f"⚠️ {source_label} returned no data. Check API Key or search query.", icon="❌")
else:
    st.error(f"API Error: {status_msg}")

# DEBUG: Inspect Raw Data
with st.expander("Debug: Raw Data Inspection"):
    if not df.empty:
        st.write("First Row Data:")
        st.json(df.iloc[0].to_dict())


# Display Data Source Status
st.caption(f"Data Source: **{source_label}**")

# --- Filtering Logic (App Side) ---
filtered_df = pd.DataFrame()
too_old_count = 0
low_score_count = 0

if not df.empty and 'viral_score' in df.columns:
    # 1. Date Filter (90 days) - only for TikTok
    if st.session_state.platform == 'TikTok':
        from datetime import datetime
        
        # Add days_old column for debug/filtering
        df['post_date_obj'] = pd.to_datetime(df['date'])
        df['days_old'] = (datetime.now() - df['post_date_obj']).dt.days
        
        # Filter: Too Old (> 90 days)
        recent_df = df[df['days_old'] <= 90]
        too_old_count = len(df) - len(recent_df)
        
        # Filter: Low Score
        if not recent_df.empty:
            filtered_df = recent_df[recent_df['viral_score'] >= st.session_state.active_min_viral].sort_values(by='viral_score', ascending=False)
            low_score_count = len(recent_df) - len(filtered_df)
        else:
            filtered_df = pd.DataFrame()
    else:  # YouTube - no date filter, just viral score
        filtered_df = df[df['viral_score'] >= st.session_state.active_min_viral].sort_values(by='viral_score', ascending=False)
        low_score_count = len(df) - len(filtered_df)

# Display Stats
col1, col2, col3, col4 = st.columns(4)
col1.metric("1. Scanned", len(df))

# Fix -0 formatting
too_old_str = f"-{too_old_count}" if too_old_count > 0 else "0"
low_score_str = f"-{low_score_count}" if low_score_count > 0 else "0"

col2.metric("2. Too Old (>90d)", too_old_str, help="Videos older than 90 days are hidden.")
col3.metric("3. Low Score", low_score_str, help=f"Videos with Viral Score < {st.session_state.active_min_viral} are hidden.")


if not filtered_df.empty:
    top_score = filtered_df['viral_score'].max()
else:
    top_score = 0
col4.metric("4. Viral Gems", len(filtered_df), f"Max: {top_score}x")

if len(df) == 0:
    st.error(f"⚠️ **No videos found!**")
    
    if status_msg != "No Data" and status_msg != "Success":
        st.error(f"**API Error:** {status_msg}")
    
    st.markdown("""
    Possible reasons:
    1. **API Key Limit**: You might have used all your free requests.
    2. **Hashtag**: Try a more popular hashtag (e.g. `#funny`, `#dogs`).
    3. **Cloud IP Block**: The API might be blocking Streamlit Server.
    """)

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

