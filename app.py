import streamlit as st
import pandas as pd
from data_fetcher import MockDataFetcher
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# Authentication must come FIRST before any st. commands
# Load credentials from secrets
try:
    credentials = {
        'cookie': st.secrets['credentials']['cookie'].to_dict(),
        'usernames': {}
    }
    
    # Convert usernames section
    for username, user_data in st.secrets['credentials']['usernames'].items():
        credentials['usernames'][username] = user_data.to_dict()
    
    # Create authenticator
    authenticator = stauth.Authenticate(
        credentials,
        st.secrets['credentials']['cookie']['name'],
        st.secrets['credentials']['cookie']['key'],
        int(st.secrets['credentials']['cookie']['expiry_days'])
    )
    
    # Render login widget
    name, authentication_status, username = authenticator.login('Login', 'main')
    
    if authentication_status == False:
        st.error('Username/password is incorrect')
        st.stop()
    elif authentication_status == None:
        st.warning('Please enter your username and password')
        st.stop()
    
    # If authenticated, get the user's API key
    user_api_key = credentials['usernames'][username]['api_key']
    
except Exception as e:
    st.error(f"Authentication setup error: {e}")
    st.info("Running without authentication (development mode)")
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

# Sidebar Filters
with st.sidebar:
    # Show logged in user
    st.success(f"👤 Logged in as: **{name}**")
    authenticator.logout('Logout', 'sidebar')
    
    st.divider()
    
    with st.form("search_form"):
        st.header("🔍 Filters")
        
        # Default to previous value if exists, else default
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

    # Initialize new session state defaults if they don't exist
    if 'active_limit' not in st.session_state:
        st.session_state.active_limit = 30

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
def load_data(hashtag, key, limit):
    if key:
        from real_data_fetcher import RealDataFetcher
        fetcher = RealDataFetcher(key)
        try:
            # Always use Default Sort (0)
            data = fetcher.fetch_posts(hashtag, limit=limit, sort_type=0)
            if not data.empty:
                return data, "Real API", "Success"
            else:
                return pd.DataFrame(), "Real API", "No Data"
        except Exception as e:
            return pd.DataFrame(), "Real API", str(e)
            
    # Fallback or Mock
    fetcher = MockDataFetcher()
    return fetcher.fetch_posts(hashtag, limit=limit), "Mock Data", "Success"

df, source_label, status_msg = load_data(st.session_state.active_hashtag, final_api_key, st.session_state.active_limit)

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

# --- Filtering Logic (App Side) ---
filtered_df = pd.DataFrame()
too_old_count = 0
low_score_count = 0

if not df.empty and 'viral_score' in df.columns:
    # 1. Date Filter (90 days)
    # We need to parse date if it's string, but fetcher returns string in 'date' col.
    # Actually fetcher doesn't return date obj, it returns str.
    # Let's rely on 'days_old' logic? Fetcher code modification didn't add 'days_old' column.
    # I should have added 'days_old' to the DF in the previous step. 
    # Wait, I didn't add it. I need to calculate it here or assume 'date' is usable.
    # 'date' is YYYY-MM-DD.
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

