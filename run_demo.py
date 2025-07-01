#!/usr/bin/env python3
"""
One-click demo runner for technical interviews
Demonstrates the entire pipeline in action
"""

import subprocess
import time
import threading
import requests
import json
from pathlib import Path

class DemoRunner:
    def __init__(self):
        self.processes = []
        
    def run_command(self, cmd, name):
        """Run command in background"""
        print(f"🚀 Starting {name}...")
        process = subprocess.Popen(cmd, shell=True)
        self.processes.append((process, name))
        return process
        
    def wait_for_service(self, url, timeout=30):
        """Wait for service to be ready"""
        for _ in range(timeout):
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(1)
        return False
    
    def demo_ml_inference(self):
        """Demonstrate ML inference capabilities"""
        print("\n🤖 Testing ML Inference API...")
        
        # Test prediction endpoint
        test_request = {
            "user_id": "user_0123",
            "product_id": "prod_045",
            "transaction_amount": 250.0,
            "context": {"session_id": "demo_session"}
        }
        
        response = requests.post(
            "http://localhost:8000/predict",
            json=test_request
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Fraud Probability: {result['fraud_probability']:.3f}")
            print(f"✅ Recommendation Score: {result['recommendation_score']:.3f}")
            print(f"✅ Inference Time: {result['inference_time_ms']:.1f}ms")
            print(f"✅ Risk Level: {result['risk_level']}")
            
            if result['inference_time_ms'] < 30:
                print("🎯 ACHIEVED <30ms LATENCY TARGET!")
            else:
                print("⚠️  Latency above 30ms target")
        else:
            print(f"❌ API Error: {response.status_code}")
    
    def run_full_demo(self):
        """Run complete pipeline demo"""
        print("🎬 Starting Real-time E-commerce ML Platform Demo")
        print("=" * 60)
        
        # Step 1: Start infrastructure
        # print("\n📦 Step 1: Starting infrastructure...")
        # self.run_command("docker-compose up -d", "Infrastructure")
        # time.sleep(10)

        # Step 1: Start infrastructure (Kafka required, Redis optional)
        print("\n📦 Step 1: Starting infrastructure...")
        self.run_command("docker-compose up kafka zookeeper -d", "Core Infrastructure")

        # Try to start Redis but don't fail if it doesn't work
        try:
            self.run_command("docker-compose up redis -d", "Redis Cache")
        except:
            print("⚠️ Redis failed to start - continuing without it")

        time.sleep(10)
        self.check_redis_availability()
        
        # Step 2: Start ML API
        print("\n🤖 Step 2: Starting ML Inference API...")
        self.run_command("python src/4_ml_inference_api.py", "ML API")
        
        if not self.wait_for_service("http://localhost:8000/health"):
            print("❌ ML API failed to start")
            return
        
        print("✅ ML API ready!")
        
        # Step 3: Start stream processor
        print("\n🔄 Step 3: Starting stream processor...")
        stream_process = threading.Thread(
            target=lambda: subprocess.run("python src/2_stream_processor.py", shell=True)
        )
        stream_process.daemon = True
        stream_process.start()
        time.sleep(3)
        
        # Step 4: Start data generation
        print("\n📊 Step 4: Starting data generation...")
        data_process = threading.Thread(
            target=lambda: subprocess.run("python src/1_data_generator.py", shell=True)
        )
        data_process.daemon = True
        data_process.start()
        time.sleep(5)
        
        # Step 5: Run batch processing
        print("\n⚡ Step 5: Running batch processing...")
        subprocess.run("python src/3_batch_processor.py", shell=True)
        
        # Step 6: Demo ML inference
        time.sleep(3)
        self.demo_ml_inference()
        
        # Step 7: Show metrics
        print("\n📈 Step 7: Performance metrics...")
        try:
            metrics = requests.get("http://localhost:8000/metrics").json()
            print(f"✅ Cache size: {metrics['feature_cache_size']}")
            print(f"✅ Model version: {metrics['model_version']}")
        except:
            print("⚠️  Could not fetch metrics")
        
        print("\n🎉 Demo complete! Press Ctrl+C to stop all services.")
        
        # Keep running until interrupted
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping demo...")
            self.cleanup()
    
    def cleanup(self):
        """Clean up processes"""
        for process, name in self.processes:
            print(f"Stopping {name}...")
            process.terminate()
        
        subprocess.run("docker-compose down", shell=True)

    
    def check_redis_availability(self):
        """Check if Redis is available"""
        try:
            import redis
            client = redis.Redis(host='localhost', port=6379)
            client.ping()
            self.redis_available = True
            print("✅ Redis detected - using for enhanced caching")
            return True
        except:
            self.redis_available = False
            print("⚠️ Redis not available - using in-memory caching")
            return False

if __name__ == "__main__":
    demo = DemoRunner()
    demo.run_full_demo()