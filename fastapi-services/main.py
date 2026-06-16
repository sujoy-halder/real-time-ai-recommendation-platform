"""
FastAPI Services for Recommendation System
Multiple services: User Service, Content Service, Analytics Service
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import redis
import logging
from datetime import datetime, timedelta
import os
import json
import pickle

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@postgres:5432/movies_db")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

app = FastAPI(
    title="Recommendation Engine API",
    description="Netflix-style real-time recommendation system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============= USER SERVICE =============

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/v1/users")
async def create_user(user_data: dict, db: Session = Depends(get_db)):
    """Create new user"""
    try:
        result = db.execute(text("""
            INSERT INTO users (username, email, created_at)
            VALUES (:username, :email, NOW())
            RETURNING id
        """), {
            "username": user_data.get("username"),
            "email": user_data.get("email")
        })
        db.commit()
        user_id = result.scalar()
        
        return {"user_id": user_id, "status": "created"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user profile"""
    try:
        user = db.execute(text("""
            SELECT id, username, email, created_at, last_active
            FROM users WHERE id = :user_id
        """), {"user_id": user_id}).fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": user[0],
            "username": user[1],
            "email": user[2],
            "created_at": user[3],
            "last_active": user[4]
        }
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/users/{user_id}/watch-history")
async def get_watch_history(user_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """Get user watch history"""
    try:
        history = db.execute(text("""
            SELECT c.id, c.title, c.thumbnail_url, ui.timestamp, ui.watch_time, c.duration
            FROM user_interactions ui
            JOIN content c ON ui.content_id = c.id
            WHERE ui.user_id = :user_id AND ui.interaction_type = 'watch'
            ORDER BY ui.timestamp DESC
            LIMIT :limit
        """), {"user_id": user_id, "limit": limit}).fetchall()
        
        return {
            "user_id": user_id,
            "history": [
                {
                    "content_id": h[0],
                    "title": h[1],
                    "thumbnail_url": h[2],
                    "watched_at": h[3],
                    "watch_time": h[4],
                    "duration": h[5]
                }
                for h in history
            ]
        }
    except Exception as e:
        logger.error(f"Error getting watch history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= CONTENT SERVICE =============

@app.get("/api/v1/content")
async def list_content(skip: int = 0, limit: int = 20, genre: str = None, db: Session = Depends(get_db)):
    """List content with pagination"""
    try:
        query = "SELECT id, title, description, thumbnail_url, genre, rating, duration FROM content"
        params = {}
        
        if genre:
            query += " WHERE genre = :genre"
            params["genre"] = genre
        
        query += " LIMIT :limit OFFSET :skip"
        params["limit"] = limit
        params["skip"] = skip
        
        content = db.execute(text(query), params).fetchall()
        
        return {
            "skip": skip,
            "limit": limit,
            "content": [
                {
                    "id": c[0],
                    "title": c[1],
                    "description": c[2],
                    "thumbnail_url": c[3],
                    "genre": c[4],
                    "rating": c[5],
                    "duration": c[6]
                }
                for c in content
            ]
        }
    except Exception as e:
        logger.error(f"Error listing content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/content/{content_id}")
async def get_content(content_id: int, db: Session = Depends(get_db)):
    """Get content details"""
    try:
        content = db.execute(text("""
            SELECT id, title, description, thumbnail_url, genre, rating, duration, release_date, cast, director
            FROM content WHERE id = :content_id
        """), {"content_id": content_id}).fetchone()
        
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")
        
        return {
            "id": content[0],
            "title": content[1],
            "description": content[2],
            "thumbnail_url": content[3],
            "genre": content[4],
            "rating": content[5],
            "duration": content[6],
            "release_date": content[7],
            "cast": content[8],
            "director": content[9]
        }
    except Exception as e:
        logger.error(f"Error getting content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/search")
async def search_content(q: str = Query(..., min_length=1), limit: int = 20, db: Session = Depends(get_db)):
    """Full-text search content"""
    try:
        search_term = f"%{q}%"
        results = db.execute(text("""
            SELECT id, title, description, thumbnail_url, genre, rating
            FROM content
            WHERE title ILIKE :term OR description ILIKE :term
            LIMIT :limit
        """), {"term": search_term, "limit": limit}).fetchall()
        
        return {
            "query": q,
            "results": [
                {
                    "id": r[0],
                    "title": r[1],
                    "description": r[2],
                    "thumbnail_url": r[3],
                    "genre": r[4],
                    "rating": r[5]
                }
                for r in results
            ]
        }
    except Exception as e:
        logger.error(f"Error searching: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= RECOMMENDATION SERVICE =============

@app.get("/api/v1/recommendations/{user_id}")
async def get_recommendations(
    user_id: int,
    limit: int = 10,
    strategy: str = "hybrid",
    db: Session = Depends(get_db)
):
    """Get personalized recommendations"""
    try:
        cache_key = f"recommendations:{user_id}:{limit}:{strategy}"
        cached = redis_client.get(cache_key)
        if cached:
            logger.info(f"Cache hit for user {user_id}")
            return json.loads(cached)
        
        # Get recommendations from database (pre-computed by Airflow)
        recommendations = db.execute(text("""
            SELECT r.content_id, r.score, c.title, c.thumbnail_url, c.genre, c.rating
            FROM recommendations r
            JOIN content c ON r.content_id = c.id
            WHERE r.user_id = :user_id
            ORDER BY r.score DESC
            LIMIT :limit
        """), {"user_id": user_id, "limit": limit}).fetchall()
        
        if not recommendations:
            # Fallback to trending
            recommendations = db.execute(text("""
                SELECT c.id, 1.0 as score, c.title, c.thumbnail_url, c.genre, c.rating
                FROM content c
                LEFT JOIN user_interactions ui ON c.id = ui.content_id
                WHERE ui.timestamp >= NOW() - INTERVAL '7 days'
                GROUP BY c.id
                ORDER BY COUNT(*) DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()
        
        result = {
            "user_id": user_id,
            "strategy": strategy,
            "recommendations": [
                {
                    "content_id": r[0],
                    "score": float(r[1]),
                    "title": r[2],
                    "thumbnail_url": r[3],
                    "genre": r[4],
                    "rating": r[5]
                }
                for r in recommendations
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        redis_client.setex(cache_key, 3600, json.dumps(result))
        return result
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/interactions")
async def record_interaction(interaction: dict, db: Session = Depends(get_db)):
    """Record user interaction (watch, like, rate)"""
    try:
        db.execute(text("""
            INSERT INTO user_interactions 
            (user_id, content_id, interaction_type, rating, timestamp)
            VALUES (:user_id, :content_id, :interaction_type, :rating, NOW())
        """), {
            "user_id": interaction.get("user_id"),
            "content_id": interaction.get("content_id"),
            "interaction_type": interaction.get("interaction_type"),
            "rating": interaction.get("rating")
        })
        db.commit()
        
        # Invalidate user's recommendations cache
        redis_client.delete(f"recommendations:{interaction.get('user_id')}:*")
        
        return {"status": "recorded", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error recording interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= ANALYTICS SERVICE =============

@app.get("/api/v1/trending")
async def get_trending(period: str = "7d", limit: int = 20, db: Session = Depends(get_db)):
    """Get trending content"""
    try:
        cache_key = f"trending:{period}:{limit}"
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        interval = {"1d": "1 day", "7d": "7 days", "30d": "30 days"}.get(period, "7 days")
        
        trending = db.execute(text(f"""
            SELECT c.id, c.title, c.thumbnail_url, c.genre, c.rating,
                   COUNT(ui.id) as interactions, AVG(ui.rating) as avg_rating
            FROM content c
            LEFT JOIN user_interactions ui ON c.id = ui.content_id
            WHERE ui.timestamp >= NOW() - INTERVAL '{interval}'
            GROUP BY c.id
            ORDER BY interactions DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()
        
        result = {
            "period": period,
            "trending": [
                {
                    "content_id": t[0],
                    "title": t[1],
                    "thumbnail_url": t[2],
                    "genre": t[3],
                    "rating": t[4],
                    "interactions": t[5],
                    "avg_rating": float(t[6]) if t[6] else 0
                }
                for t in trending
            ]
        }
        
        redis_client.setex(cache_key, 3600, json.dumps(result))
        return result
        
    except Exception as e:
        logger.error(f"Error getting trending: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/user/{user_id}")
async def user_analytics(user_id: int, db: Session = Depends(get_db)):
    """Get user engagement analytics"""
    try:
        analytics = db.execute(text("""
            SELECT 
                COUNT(CASE WHEN interaction_type = 'watch' THEN 1 END) as total_watches,
                COUNT(CASE WHEN interaction_type = 'like' THEN 1 END) as total_likes,
                AVG(rating) as avg_rating,
                SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as high_rated,
                MAX(timestamp) as last_active
            FROM user_interactions
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchone()
        
        return {
            "user_id": user_id,
            "total_watches": analytics[0] or 0,
            "total_likes": analytics[1] or 0,
            "avg_rating": float(analytics[2]) if analytics[2] else 0,
            "high_rated_count": analytics[3] or 0,
            "last_active": analytics[4]
        }
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
