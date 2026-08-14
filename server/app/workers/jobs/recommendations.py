from app.services.recommendations.service import recommend

def rebuild_recommendations(db, profile_id=None, limit=50):
    return recommend(db, profile_id=profile_id, limit=limit)
