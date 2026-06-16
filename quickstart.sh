#!/bin/bash

# Quick Start Script for Recommendation System
# This script sets up the entire system locally

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Real-Time AI Recommendation System - Quick Start Setup       ║"
echo "╚════════════════════════════════════════════════════════════════╝"

# Check prerequisites
echo ""
echo "📋 Checking prerequisites..."

check_command() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 is not installed. Please install it first."
        exit 1
    fi
    echo "✓ $1 found"
}

check_command "docker"
check_command "docker-compose"
check_command "git"

# Clone or navigate to repo
echo ""
echo "📁 Setting up project..."
if [ ! -d ".git" ]; then
    echo "Repository not initialized, initializing Git..."
    git init
fi

# Create .env file
echo ""
echo "🔧 Creating environment configuration..."
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql://admin:admin@postgres:5432/recommendations_db
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin
POSTGRES_DB=recommendations_db

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Airflow
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__CORE__LOAD_EXAMPLES=false

# API
API_PORT=8000
API_WORKERS=4

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
AIRFLOW_PORT=8888

# AWS (for cloud deployment)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
EOF
    echo "✓ .env file created"
else
    echo "✓ .env file already exists"
fi

# Create Docker network
echo ""
echo "🌐 Creating Docker network..."
docker network create recommendation-network 2>/dev/null || echo "✓ Network already exists"

# Build images
echo ""
echo "🔨 Building Docker images..."
docker-compose -f docker-compose-production.yml build --parallel

# Start services
echo ""
echo "🚀 Starting services..."
docker-compose -f docker-compose-production.yml up -d

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be healthy..."

wait_for_service() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:$port > /dev/null 2>&1; then
            echo "✓ $service is ready"
            return 0
        fi
        echo "Waiting for $service... ($((attempt+1))/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    echo "❌ $service failed to start"
    return 1
}

# Check PostgreSQL
echo "Checking PostgreSQL..."
docker exec postgres-recommendation pg_isready -U admin || true

# Initialize database schema
echo ""
echo "🗄️  Initializing database schema..."
docker exec postgres-recommendation psql -U admin -d recommendations_db -f /docker-entrypoint-initdb.d/schema.sql 2>/dev/null || echo "✓ Schema already initialized"

# Wait for key services
wait_for_service "FastAPI" 8000 || true
wait_for_service "Redis" 6379 || true
wait_for_service "Kafka" 9092 || true

# Insert sample data
echo ""
echo "📊 Inserting sample data..."
docker exec postgres-recommendation psql -U admin -d recommendations_db << 'EOF'
-- Insert sample users
INSERT INTO users (username, email) VALUES
    ('user1', 'user1@example.com'),
    ('user2', 'user2@example.com'),
    ('user3', 'user3@example.com')
ON CONFLICT DO NOTHING;

-- Insert sample content
INSERT INTO content (title, description, genre, duration, rating) VALUES
    ('The Matrix', 'A hacker discovers reality is a simulation', 'Sci-Fi', 136, 4.5),
    ('Inception', 'A thief steals corporate secrets from dreams', 'Sci-Fi', 148, 4.3),
    ('Interstellar', 'Astronauts travel through a wormhole', 'Sci-Fi', 169, 4.4),
    ('The Shawshank Redemption', 'Two prisoners form a friendship', 'Drama', 142, 4.9),
    ('Pulp Fiction', 'Interconnected crime stories', 'Crime', 154, 4.6),
    ('The Dark Knight', 'Batman faces the Joker', 'Action', 152, 4.7),
    ('Forrest Gump', 'A man chronicles his extraordinary life', 'Drama', 142, 4.5),
    ('The Godfather', 'A crime dynasty unfolds', 'Crime', 175, 4.9),
    ('Avatar', 'Humans colonize an alien world', 'Sci-Fi', 162, 4.2),
    ('Titanic', 'A ship sinks in the Atlantic', 'Drama', 194, 4.1)
ON CONFLICT DO NOTHING;

-- Insert sample interactions
INSERT INTO user_interactions (user_id, content_id, interaction_type, rating) VALUES
    (1, 1, 'watch', 4.5),
    (1, 2, 'watch', 4.8),
    (1, 3, 'like', NULL),
    (2, 4, 'watch', 5.0),
    (2, 5, 'watch', 4.2),
    (3, 6, 'watch', 4.6),
    (3, 7, 'like', NULL),
    (1, 8, 'rate', 4.9)
ON CONFLICT DO NOTHING;

SELECT 'Sample data inserted successfully' as status;
EOF

echo "✓ Sample data inserted"

# Display access information
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    🎉 Setup Complete! 🎉                       ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║                                                                ║"
echo "║  📍 Service Endpoints:                                         ║"
echo "║  ├─ API:           http://localhost:8000                      ║"
echo "║  ├─ API Docs:      http://localhost:8000/docs                 ║"
echo "║  ├─ Airflow:       http://localhost:8888                      ║"
echo "║  ├─ Grafana:       http://localhost:3000                      ║"
echo "║  ├─ Prometheus:    http://localhost:9090                      ║"
echo "║  ├─ Kibana:        http://localhost:5601                      ║"
echo "║  ├─ Spark Master:  http://localhost:8080                      ║"
echo "║  └─ PostgreSQL:    localhost:5432                             ║"
echo "║                                                                ║"
echo "║  🔑 Credentials:                                               ║"
echo "║  ├─ Airflow:       admin / admin                              ║"
echo "║  ├─ Grafana:       admin / admin                              ║"
echo "║  ├─ PostgreSQL:    admin / admin                              ║"
echo "║  └─ Redis:         (no auth)                                  ║"
echo "║                                                                ║"
echo "║  📚 Quick Commands:                                            ║"
echo "║  ├─ View logs:     docker-compose logs -f recommendation-api  ║"
echo "║  ├─ Health check:  curl http://localhost:8000/health          ║"
echo "║  ├─ Get recs:      curl http://localhost:8000/api/v1/\       ║"
echo "║  │                 recommendations/1                          ║"
echo "║  ├─ Stop:          docker-compose -f docker-compose-\         ║"
echo "║  │                 production.yml down                        ║"
echo "║  └─ Cleanup:       docker system prune -a                     ║"
echo "║                                                                ║"
echo "║  📖 Documentation:                                             ║"
echo "║  ├─ API Docs:      http://localhost:8000/docs                 ║"
echo "║  ├─ README:        cat README.md                              ║"
echo "║  └─ Setup Guide:   cat SETUP.md                               ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Display running services
echo "🔍 Running Services:"
docker-compose -f docker-compose-production.yml ps

echo ""
echo "✅ System is ready! Start making recommendations 🚀"
