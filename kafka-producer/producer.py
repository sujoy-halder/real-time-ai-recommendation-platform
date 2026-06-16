"""
Kafka Producer: Real-time event streaming
Sends user interactions (watch, click, like, rate) to Kafka topics
"""

import json
import logging
from kafka import KafkaProducer
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class EventProducer:
    def __init__(self):
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092").split(",")
        
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3,
            max_in_flight_requests_per_connection=1
        )
        
        self.topics = {
            'user_events': 'user-events',
            'watch_events': 'watch-events',
            'like_events': 'like-events',
            'rating_events': 'rating-events',
            'search_events': 'search-events'
        }
        
        logger.info("Kafka producer initialized")
    
    def send_watch_event(self, user_id: int, content_id: int, duration: int, watch_time: int):
        """Send watch event"""
        event = {
            'user_id': user_id,
            'content_id': content_id,
            'duration': duration,
            'watch_time': watch_time,
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'watch'
        }
        
        self.producer.send(self.topics['watch_events'], value=event)
        logger.info(f"Watch event sent: user={user_id}, content={content_id}")
    
    def send_like_event(self, user_id: int, content_id: int, liked: bool):
        """Send like/unlike event"""
        event = {
            'user_id': user_id,
            'content_id': content_id,
            'liked': liked,
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'like'
        }
        
        self.producer.send(self.topics['like_events'], value=event)
        logger.info(f"Like event sent: user={user_id}, content={content_id}, liked={liked}")
    
    def send_rating_event(self, user_id: int, content_id: int, rating: float):
        """Send rating event"""
        if not 0 <= rating <= 5:
            logger.warning(f"Invalid rating: {rating}")
            return
        
        event = {
            'user_id': user_id,
            'content_id': content_id,
            'rating': rating,
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'rating'
        }
        
        self.producer.send(self.topics['rating_events'], value=event)
        logger.info(f"Rating event sent: user={user_id}, content={content_id}, rating={rating}")
    
    def send_search_event(self, user_id: int, query: str, results_count: int):
        """Send search event"""
        event = {
            'user_id': user_id,
            'query': query,
            'results_count': results_count,
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'search'
        }
        
        self.producer.send(self.topics['search_events'], value=event)
        logger.info(f"Search event sent: user={user_id}, query={query}")
    
    def flush(self):
        """Flush pending messages"""
        self.producer.flush()
    
    def close(self):
        """Close producer"""
        self.producer.close()
