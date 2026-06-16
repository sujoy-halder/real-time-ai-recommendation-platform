-- PostgreSQL Schema for Recommendation System

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP,
    preferences JSONB
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);

-- Content table
CREATE TABLE IF NOT EXISTS content (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    genre VARCHAR(100),
    duration INT,
    rating DECIMAL(3,1),
    release_date DATE,
    thumbnail_url VARCHAR(500),
    poster_url VARCHAR(500),
    cast TEXT,
    director VARCHAR(255),
    tags TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_content_genre ON content(genre);
CREATE INDEX idx_content_rating ON content(rating);
CREATE INDEX idx_content_created_at ON content(created_at);

-- User Interactions table
CREATE TABLE IF NOT EXISTS user_interactions (
    id BIGSERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_id INT NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    interaction_type VARCHAR(50) NOT NULL, -- 'watch', 'like', 'unlike', 'rate', 'click', 'search'
    rating DECIMAL(2,1),
    watch_time INT,  -- in seconds
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_interactions_user_id ON user_interactions(user_id);
CREATE INDEX idx_interactions_content_id ON user_interactions(content_id);
CREATE INDEX idx_interactions_timestamp ON user_interactions(timestamp);
CREATE INDEX idx_interactions_user_time ON user_interactions(user_id, timestamp DESC);

-- Pre-computed Recommendations table
CREATE TABLE IF NOT EXISTS recommendations (
    id BIGSERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_id INT NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    score DECIMAL(5,3) NOT NULL,
    strategy VARCHAR(50),  -- 'cf', 'cb', 'hybrid', 'trending'
    generated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_recommendations_user_id ON recommendations(user_id);
CREATE INDEX idx_recommendations_generated_at ON recommendations(generated_at);
CREATE INDEX idx_recommendations_score ON recommendations(user_id, score DESC);

-- Content Features for similarity (cached)
CREATE TABLE IF NOT EXISTS content_features (
    id SERIAL PRIMARY KEY,
    content_id INT NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    feature_vector FLOAT8[] NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_content_features_content_id ON content_features(content_id);

-- User Embeddings for collaborative filtering
CREATE TABLE IF NOT EXISTS user_embeddings (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    embedding FLOAT8[] NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_embeddings_user_id ON user_embeddings(user_id);

-- Content metadata cache
CREATE TABLE IF NOT EXISTS content_metadata (
    id SERIAL PRIMARY KEY,
    content_id INT NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    metadata JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_content_metadata_content_id ON content_metadata(content_id);

-- User Preferences
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    preferred_genres TEXT[],
    language VARCHAR(10),
    subtitle_enabled BOOLEAN DEFAULT true,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);

-- Analytics table
CREATE TABLE IF NOT EXISTS analytics (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_users INT,
    active_users INT,
    total_watches INT,
    avg_rating DECIMAL(3,1),
    trending_content_id INT REFERENCES content(id),
    recorded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_analytics_date ON analytics(date);
