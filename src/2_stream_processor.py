#!/usr/bin/env python3
"""
Real-time feature computation using Kafka Streams concepts
Demonstrates: Stream processing, windowing, real-time aggregations
"""

import json
import time
from collections import defaultdict, deque
from kafka import KafkaConsumer, KafkaProducer
import redis
from datetime import datetime, timedelta
import threading
from utils import SmartCache

class RealTimeFeatureProcessor:
    def __init__(self):
        self.consumer = KafkaConsumer(
            'user_events', 'transactions',
            bootstrap_servers=['localhost:9092'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='feature_processor'
        )
        self.cache = SmartCache()
        
        self.producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        # Redis for real-time feature storage
        # self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # In-memory sliding windows for ultra-fast computation
        self.user_windows = defaultdict(lambda: {
            'events_1h': deque(maxlen=3600),  # 1 hour sliding window
            'purchases_24h': deque(maxlen=86400),  # 24 hour window
            'session_events': deque(maxlen=100),
            'categories_browsed': set(),
            'last_activity': time.time()
        })
    
    def process_user_event(self, event):
        """Process user events and update real-time features"""
        user_id = event['user_id']
        current_time = time.time()
        
        user_data = self.user_windows[user_id]
        user_data['events_1h'].append(current_time)
        user_data['session_events'].append(event)
        user_data['categories_browsed'].add(event['category'])
        user_data['last_activity'] = current_time
        
        if event['event_type'] == 'purchase':
            user_data['purchases_24h'].append(current_time)
        
        # Calculate real-time features
        features = self.calculate_features(user_id, current_time)
        
        # Store in Redis for ML inference
        # self.redis_client.hset(f"features:{user_id}", mapping=features)
        self.cache.hset(f"features:{user_id}", features)
        
        # Send enriched event downstream
        enriched_event = {**event, 'real_time_features': features}
        self.producer.send('enriched_events', enriched_event)
        
        return features
    
    def calculate_features(self, user_id: str, current_time: float) -> dict:
        """Calculate real-time ML features with sliding windows"""
        user_data = self.user_windows[user_id]
        
        # Clean old data from sliding windows
        cutoff_1h = current_time - 3600
        cutoff_24h = current_time - 86400
        
        recent_events_1h = [t for t in user_data['events_1h'] if t > cutoff_1h]
        recent_purchases_24h = [t for t in user_data['purchases_24h'] if t > cutoff_24h]
        
        features = {
            # Velocity features
            'events_last_hour': len(recent_events_1h),
            'purchases_last_24h': len(recent_purchases_24h),
            
            # Session features  
            'session_length': len(user_data['session_events']),
            'categories_in_session': len(user_data['categories_browsed']),
            'time_since_last_activity': current_time - user_data['last_activity'],
            
            # Behavioral patterns
            'avg_events_per_hour': len(recent_events_1h) if recent_events_1h else 0,
            'is_weekend': datetime.now().weekday() >= 5,
            'hour_of_day': datetime.now().hour,
            
            # Risk indicators
            'rapid_activity': 1 if len(recent_events_1h) > 100 else 0,
            'burst_purchases': 1 if len(recent_purchases_24h) > 5 else 0
        }
        
        return features
    
    def start_processing(self):
        """Main stream processing loop"""
        print("🔄 Starting real-time feature processing...")
        
        for message in self.consumer:
            try:
                event = message.value
                topic = message.topic
                
                if topic == 'user_events':
                    features = self.process_user_event(event)
                    print(f"✅ Processed {event['event_type']} for {event['user_id']} - {len(features)} features")
                
                elif topic == 'transactions':
                    # Process transaction for fraud detection
                    self.process_transaction(event)
                    
            except Exception as e:
                print(f"❌ Processing error: {e}")
    
    def process_transaction(self, transaction):
        """Process transactions for fraud detection features"""
        user_id = transaction['user_id']
        
        # Get user's real-time features
        features = self.redis_client.hgetall(f"features:{user_id}")
        
        # Add transaction-specific features
        fraud_features = {
            **features,
            'transaction_amount': transaction['amount'],
            'payment_method': transaction['payment_method'],
            'risk_score': transaction['risk_score'],
            'unusual_amount': 1 if float(transaction['amount']) > 500 else 0
        }
        
        # Send to fraud detection topic
        fraud_event = {**transaction, 'fraud_features': fraud_features}
        self.producer.send('fraud_detection', fraud_event)

if __name__ == "__main__":
    processor = RealTimeFeatureProcessor()
    processor.start_processing()