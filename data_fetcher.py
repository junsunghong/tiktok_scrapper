import pandas as pd
import random
from datetime import datetime, timedelta
from virality_scorer import calculate_viral_score, classify_virality

class DataFetcher:
    def fetch_posts(self, hashtag: str, limit: int = 20) -> pd.DataFrame:
        raise NotImplementedError

class MockDataFetcher(DataFetcher):
    def fetch_posts(self, hashtag: str, limit: int = 50) -> pd.DataFrame:
        """
        Generates mock data for a given hashtag to simulate an API response.
        """
        data = []
        
        # Sample content templates for SaaS/Software niche
        templates = [
            "5 Tools every developer needs",
            "Day in the life of a software engineer",
            "How I built a SaaS in 30 days",
            "Stop using print() debugging!",
            "Python vs JavaScript: The Truth",
            "My $10k/mo Micro-SaaS Stack",
            "Why your code is slow",
            "Coding setup tour 2026",
            "Junior vs Senior Dev: Code Review",
            "The AI tool that writes code for you"
        ]

        for i in range(limit):
            # Randomly generate metrics
            followers = random.randint(500, 500000)
            
            # Simulate "Viral" posts (small followers, huge views)
            is_viral_candidate = random.random() < 0.2 # 20% chance of being viral
            if is_viral_candidate and followers < 10000:
                views = random.randint(50000, 500000) # Big views for small account
            else:
                # Normal distribution
                views = int(followers * random.uniform(0.1, 1.5))
            
            likes = int(views * random.uniform(0.05, 0.15)) # 5-15% like rate
            score = calculate_viral_score(views, followers)
            label = classify_virality(score)
            
            post = {
                "id": f"post_{i}",
                "title": random.choice(templates),
                "author": f"user_{random.randint(1000, 9999)}",
                "hashtag": hashtag,
                "followers": followers,
                "views": views,
                "likes": likes,
                "date": (datetime.now() - timedelta(days=random.randint(0, 7))).strftime("%Y-%m-%d"),
                "viral_score": score,
                "virality_label": label,
                "thumbnail_url": f"https://picsum.photos/seed/{i}/300/500" # Placeholder image
            }
            data.append(post)
            
        return pd.DataFrame(data)
