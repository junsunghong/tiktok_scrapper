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
    
    def search_videos(self, query: str, max_results: int = 25, order: str = 'relevance',
                      video_duration: str = 'any', page_token: str = None):
        """
        Search YouTube videos with filters and calculate viral scores
        
        Args:
            query: Search keywords/hashtag
            max_results: 10-50
            order: 'relevance', 'date', 'viewCount', 'rating'
            video_duration: 'any', 'short' (<4min), 'medium', 'long'
            page_token: For pagination (nextPageToken from previous response)
            
        Returns:
            tuple: (DataFrame, next_token, prev_token)
        """
        # Search for videos
        search_response = self.youtube.search().list(
            q=query,
            part='id,snippet',
            type='video',
            maxResults=max_results,
            order=order,
            videoDuration=video_duration,
            pageToken=page_token
        ).execute()
        
        if not search_response.get('items'):
            return pd.DataFrame(), None, None
        
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
        
        # Parse videos
        parsed_data = []
        for video in videos_response['items']:
            snippet = video['snippet']
            statistics = video['statistics']
            content_details = video['contentDetails']
            
            # Extract data
            video_id = video['id']
            channel_id = snippet['channelId']
            title = snippet['title']
            description = snippet['description']
            thumbnail = snippet['thumbnails'].get('high', {}).get('url', '')
            published_at = snippet['publishedAt']
            channel_title = snippet['channelTitle']
            
            views = int(statistics.get('viewCount', 0))
            likes = int(statistics.get('likeCount', 0))
            comments = int(statistics.get('commentCount', 0))
            
            # Duration and video type
            duration_iso = content_details['duration']
            duration_seconds = int(isodate.parse_duration(duration_iso).total_seconds())
            video_type = 'Short' if duration_seconds < 60 else 'Long-form'
            
            # Viral score
            subscribers = subscriber_map.get(channel_id, 1)
            viral_score = calculate_viral_score(views, subscribers)
            virality_label = classify_virality(viral_score)
            
            # Parse date
            post_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            
            parsed_data.append({
                'id': video_id,
                'title': title,
                'author': channel_title,
                'hashtag': query,
                'followers': subscribers,
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
        
        df = pd.DataFrame(parsed_data)
        
        # Pagination tokens
        next_token = search_response.get('nextPageToken')
        prev_token = search_response.get('prevPageToken')
        
        return df, next_token, prev_token
