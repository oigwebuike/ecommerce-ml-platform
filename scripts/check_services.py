#!/usr/bin/env python3
"""
Service availability checker for the ML platform
"""

def check_service_availability():
    """Check which services are available"""
    services = {
        'kafka': False,
        'redis': False,
        'postgres': False
    }
    
    # Check Kafka
    try:
        from kafka import KafkaConsumer
        consumer = KafkaConsumer(bootstrap_servers=['localhost:9092'])
        consumer.close()
        services['kafka'] = True
        print("✅ Kafka: Available")
    except:
        print("❌ Kafka: Not available")
    
    # Check Redis
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379)
        client.ping()
        services['redis'] = True
        print("✅ Redis: Available (enhanced caching)")
    except:
        print("⚠️ Redis: Not available (using in-memory cache)")
    
    return services

if __name__ == "__main__":
    check_service_availability()