def calculate_viral_score(views: int, followers: int) -> float:
    """
    Calculates the 'Viral Score' based on the Views-to-Follower Ratio.
    
    Formula: Views / Followers
    
    Example:
    - 50k views / 1k followers = 50.0 (MEGA VIRAL)
    - 100k views / 100k followers = 1.0 (Normal)
    """
    if followers == 0:
        return 0.0
    return round(views / followers, 2)

def classify_virality(score: float) -> str:
    """
    Classifies the viral score into a human-readable label.
    """
    if score >= 10.0:
        return "🔥 Mega Viral"
    elif score >= 3.0:
        return "🚀 Trending"
    elif score >= 1.0:
        return "👍 Popular"
    else:
        return "😐 Normal"
