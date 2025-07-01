#!/usr/bin/env python3
"""
Real-time event generator with Kafka streaming
Demonstrates: Kafka, distributed event processing, schema design
"""

import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict
import uuid
from kafka import KafkaProducer
import threading

class EcommerceEventGenerator:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8')
        )
        
        # Realistic data distributions
        self.users = [f"user_{i:04d}" for i in range(1, 1001)]
        self.products = [f"prod_{i:03d}" for i in range(1, 201)]
        self.categories = ["electronics", "clothing", "books", "home", "sports"]
        
    def generate_user_event(self) -> Dict:
        """Generate realistic user interaction events"""
        user_id = random.choice(self.users)
        event_types = ["view", "cart_add", "purchase", "search"]
        weights = [0.6, 0.2, 0.1, 0.1]  # Realistic conversion funnel
        
        return {
            "event_id": str(uuid.uuid4()),
            "user_id": user_id,
            "event_type": random.choices(event_types, weights=weights)[0],
            "product_id": random.choice(self.products),
            "category": random.choice(self.categories),
            "price": round(random.uniform(10, 500), 2),
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": f"session_{random.randint(1, 100)}",
            # Add features for ML
            "user_agent": random.choice(["mobile", "desktop", "tablet"]),
            "location": random.choice(["US", "EU", "ASIA"]),
        }
    
    def generate_transaction_event(self) -> Dict:
        """Generate transaction events with fraud indicators"""
        return {
            "transaction_id": str(uuid.uuid4()),
            "user_id": random.choice(self.users),
            "amount": round(random.uniform(20, 1000), 2),
            "payment_method": random.choice(["credit", "debit", "paypal"]),
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
            "risk_score": random.uniform(0, 1),  # For fraud detection
            "velocity_check": random.choice([True, False])
        }
    
    def start_streaming(self, events_per_second: int = 50):
        """Start producing events to Kafka topics"""
        print(f"🚀 Starting event stream at {events_per_second} events/sec")
        
        while True:
            try:
                # Generate user events (80% of traffic)
                if random.random() < 0.8:
                    event = self.generate_user_event()
                    self.producer.send(
                        'user_events',
                        key=event['user_id'],
                        value=event
                    )
                
                # Generate transactions (20% of traffic)
                else:
                    event = self.generate_transaction_event()
                    self.producer.send(
                        'transactions',
                        key=event['user_id'],
                        value=event
                    )
                
                time.sleep(1.0 / events_per_second)
                
            except KeyboardInterrupt:
                print("Stopping event generation...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)

if __name__ == "__main__":
    generator = EcommerceEventGenerator()
    generator.start_streaming()