"""
YouTube Data API v3 Fetcher
Fetches videos with metadata, statistics, and viral score calculation
"""
import pandas as pd
from datetime import datetime
import isodate


def calculate_viral_score(views: int, subscribers: int) -> float:
    """Calculate viral score: views / subscribers"""
    if subscribers == 0:
        subscribers = 1
    return round(views / subscribers, 2)


def classify_virality(score: float) -> str:
    """Classify video based on viral score"""
    if score >= 10:
        return "🔥 Mega Viral"
    elif score >= 5:
        return "⚡ Viral"
    elif score >= 2:
        return "📈 Trending"
    else:
        return "📊 Normal"


class YouTubeDataFetcher:
    def __init__(self, api_key: str):
        from googleapiclient.discovery import build
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)
    
    def search_videos(self, query: str, target_results: int = 25, order: str = 'date',
                      video_duration: str = 'any', min_views: int = 0, min_subscribers: int = 0,
                      page_token: str = None, max_api_calls: int = 5):
        """
        Search YouTube videos with filters and calculate viral scores.
        Auto-paginates until target_results filtered videos are collected.
        
        Args:
            query: Search keywords/hashtag
            target_results: Target number of FILTERED results to return (10-50)
            order: 'relevance', 'date', 'viewCount', 'rating'
            video_duration: 'any', 'short' (<4min), 'medium', 'long'
            min_views: Minimum view count filter
            min_subscribers: Minimum subscriber count filter
            page_token: For pagination (nextPageToken from previous response)
            max_api_calls: Maximum number of API calls to prevent quota exhaustion
            
        Returns:
            tuple: (DataFrame, next_token, prev_token)
        """
        all_videos = []
        current_page_token = page_token
        api_calls = 0
        
        # Keep fetching until we have enough filtered results or hit max calls
        while len(all_videos) < target_results and api_calls < max_api_calls:
            api_calls += 1
            
            # Search for videos (50 per page to minimize API calls)
            search_response = self.youtube.search().list(
                q=query,
                part='id,snippet',
                type='video',
                maxResults=50,  # Max allowed by API
                order=order,
                videoDuration=video_duration,
                pageToken=current_page_token
            ).execute()
            
            if not search_response.get('items'):
                break
            
            video_ids = [item['id']['videoId'] for item in search_response['items']]
            
            # Get detailed video statistics
            videos_response = self.youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(video_ids)
            ).execute()
            
            # Get unique channel IDs
            channel_ids = list(set([video['snippet']['channelId'] for video in videos_response['items']]))
            
            # Get subscriber counts for all channels
            channels_response = self.youtube.channels().list(
                part='statistics',
                id=','.join(channel_ids)
            ).execute()
            
            # Map channel_id -> subscriber_count
            subscriber_map = {}
            for channel in channels_response['items']:
                channel_id = channel['id']
                subscriber_count = int(channel['statistics'].get('subscriberCount', 1))
                subscriber_map[channel_id] = subscriber_count if subscriber_count > 0 else 1
            
            # Parse videos and apply filters
            for video in videos_response['items']:
                snippet = video['snippet']
                statistics = video['statistics']
                content_details = video['contentDetails']
                
                # Extract data
                video_id = video['id']
                channel_id = snippet['channelId']
                views = int(statistics.get('viewCount', 0))
                subscribers = subscriber_map.get(channel_id, 1)
                
                # Apply filters
                if views < min_views or subscribers < min_subscribers:
                    continue
                
                title = snippet['title']
                description = snippet['description']
                thumbnail = snippet['thumbnails'].get('high', {}).get('url', '')
                published_at = snippet['publishedAt']
                channel_title = snippet['channelTitle']
                
                likes = int(statistics.get('likeCount', 0))
                comments = int(statistics.get('commentCount', 0))
                
                # Duration and video type
                duration_iso = content_details.get('duration', 'PT0S')
                try:
                    duration_seconds = int(isodate.parse_duration(duration_iso).total_seconds())
                except:
                    duration_seconds = 0  # Default to 0 if parsing fails
                video_type = 'Short' if duration_seconds < 60 else 'Long-form'
                
                # Viral score
                viral_score = calculate_viral_score(views, subscribers)
                virality_label = classify_virality(viral_score)
                
                # Parse date
                post_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                
                all_videos.append({
                    'id': video_id,
                    'title': title,
                    'author': channel_title,
                    'hashtag': query,
                    'followers': subscribers,  # Keep 'followers' for compatibility, rename in display
                    'views': views,
                    'likes': likes,
                    'comments': comments,
                    'date': post_date.strftime('%Y-%m-%d'),
                    'viral_score': viral_score,
                    'virality_label': virality_label,
                    'video_type': video_type,
                    'duration_seconds': duration_seconds,
                    'thumbnail_url': thumbnail,
                    'video_url': f"https://www.youtube.com/watch?v={video_id}"
                })
                
                # Stop if we have enough
                if len(all_videos) >= target_results:
                    break
            
            # Get next page token
            current_page_token = search_response.get('nextPageToken')
            if not current_page_token:
                break  # No more pages
        
        df = pd.DataFrame(all_videos[:target_results])  # Trim to exact target
        
        # Pagination tokens (for manual navigation if needed)
        next_token = search_response.get('nextPageToken') if 'search_response' in locals() else None
        prev_token = search_response.get('prevPageToken') if 'search_response' in locals() else None
        
        return df, next_token, prev_token
