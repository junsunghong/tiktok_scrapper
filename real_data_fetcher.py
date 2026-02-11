import requests
import pandas as pd
from datetime import datetime
from virality_scorer import calculate_viral_score, classify_virality
from data_fetcher import DataFetcher

class RealDataFetcher(DataFetcher):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://tiktok-scraper7.p.rapidapi.com/feed/search"
        self.host = "tiktok-scraper7.p.rapidapi.com"

    def fetch_posts(self, hashtag: str, limit: int = 20) -> pd.DataFrame:
        """
        Fetches real videos from TikTok via RapidAPI.
        """
        # Ensure hashtag has #
        if not hashtag.startswith("#"):
            hashtag = f"#{hashtag}"

        querystring = {
            "keywords": hashtag,
            "count": str(limit),
            "region": "us",
            "publish_time": "0", # Any time
            "sort_type": "0" # Default sort (Relevance/General)
        }

        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host
        }

        try:
            response = requests.get(self.url, headers=headers, params=querystring)
            response.raise_for_status()
            json_data = response.json()
            
            # Check if 'data' and 'videos' exist
            if "data" not in json_data or "videos" not in json_data["data"]:
                print(f"API Response Warning: {json_data}")
                return pd.DataFrame()

            videos = json_data["data"]["videos"]
            if videos:
                print(f"DEBUG: First video author: {videos[0].get('author')}")
                print(f"DEBUG: First video create_time: {videos[0].get('create_time')}")
            
            parsed_data = []

            for video in videos:
                # Extract Metrics
                views = video.get("play_count", 0)
                likes = video.get("digg_count", 0)
                author = video.get("author", {})
                
                # Fetch real follower count (requires extra API call)
                # To save quota/time, we could only doing this for high-view videos, 
                # but for accuracy we do it for all.
                try:
                    followers = self._fetch_user_followers(author.get("unique_id"))
                except:
                    followers = 1 # Fallback
                
                if followers == 0:
                    followers = 1

                score = calculate_viral_score(views, followers)
                label = classify_virality(score)
                
                # Date Filtering (Last 90 Days)
                create_time = video.get("create_time", 0)
                post_date = datetime.fromtimestamp(create_time)
                days_old = (datetime.now() - post_date).days
                
                if days_old > 90:
                    continue # Skip old content

                # Try animated cover first (often works better), then static covers
                # We use wsrv.nl as a transparent proxy to bypass TikTok's hotlink protection (403 Forbidden)
                raw_thumbnail = video.get("ai_dynamic_cover") or video.get("origin_cover") or video.get("cover")
                
                if raw_thumbnail:
                    # Encode URL for the proxy
                    from urllib.parse import quote
                    thumbnail = f"https://wsrv.nl/?url={quote(raw_thumbnail)}&w=300&h=500&fit=cover"
                else:
                    thumbnail = "https://picsum.photos/300/500"

                post = {
                    "id": video.get("video_id", ""),
                    "title": video.get("title", "No Title"),
                    "author": author.get("nickname", "Unknown"),
                    "hashtag": hashtag,
                    "followers": followers,
                    "views": views,
                    "likes": likes,
                    "date": post_date.strftime("%Y-%m-%d"),
                    "viral_score": score,
                    "virality_label": label,
                    "thumbnail_url": thumbnail,
                    "video_url": f"https://www.tiktok.com/@{author.get('unique_id', '')}/video/{video.get('video_id', '')}"
                }
                parsed_data.append(post)

            return pd.DataFrame(parsed_data)

        except Exception as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame()

    def _fetch_user_followers(self, unique_id: str) -> int:
        """
        Fetches the follower count for a specific user.
        """
        if not unique_id:
            return 1
            
        url = "https://tiktok-scraper7.p.rapidapi.com/user/info"
        querystring = {"unique_id": unique_id}
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host
        }
        
        try:
            response = requests.get(url, headers=headers, params=querystring)
            data = response.json()
            return data.get("data", {}).get("stats", {}).get("followerCount", 1)
        except:
            return 1
