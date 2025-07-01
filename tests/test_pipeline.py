#!/usr/bin/env python3
"""
Comprehensive tests for the ML platform pipeline
"""

import pytest
import asyncio
import json
import time
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch
import requests
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils import setup_logging, get_timestamp

class TestDataGeneration:
    """Test data generation and Kafka integration"""
    
    def test_event_generation(self):
        """Test event generator creates valid events"""
        # Import here to avoid import issues during test discovery
        from src import 1_data_generator
        
        generator = 1_data_generator.EcommerceEventGenerator()
        event = generator.generate_user_event()
        
        # Validate event structure
        required_fields = [
            'event_id', 'user_id', 'event_type', 'product_id', 
            'category', 'price', 'timestamp', 'session_id'
        ]
        
        for field in required_fields:
            assert field in event, f"Missing required field: {field}"
        
        # Validate data types and ranges
        assert isinstance(event['price'], float)
        assert 10 <= event['price'] <= 500
        assert event['event_type'] in ['view', 'cart_add', 'purchase', 'search']
        assert event['category'] in ['electronics', 'clothing', 'books', 'home', 'sports']
    
    def test_transaction_generation(self):
        """Test transaction event generation"""
        from src import 1_data_generator
        
        generator = 1_data_generator.EcommerceEventGenerator()
        transaction = generator.generate_transaction_event()
        
        required_fields = [
            'transaction_id', 'user_id', 'amount', 'payment_method',
            'timestamp', 'ip_address', 'risk_score'
        ]
        
        for field in required_fields:
            assert field in transaction
        
        assert 20 <= transaction['amount'] <= 1000
        assert 0 <= transaction['risk_score'] <= 1

class TestStreamProcessing:
    """Test real-time stream processing"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        with patch('redis.Redis') as mock:
            mock_client = Mock()
            mock.return_value = mock_client
            yield mock_client
    
    def test_feature_calculation(self, mock_redis):
        """Test real-time feature calculation"""
        from src import 2_stream_processor
        
        processor = 2_stream_processor.RealTimeFeatureProcessor()
        
        # Mock event
        event = {
            'user_id': 'test_user_001',
            'event_type': 'purchase',
            'product_id': 'prod_001',
            'category': 'electronics',
            'price': 299.99,
            'timestamp': get_timestamp()
        }
        
        features = processor.process_user_event(event)
        
        # Validate feature structure
        expected_features = [
            'events_last_hour', 'purchases_last_24h', 'session_length',
            'categories_in_session', 'time_since_last_activity'
        ]
        
        for feature in expected_features:
            assert feature in features
    
    def test_sliding_window(self):
        """Test sliding window functionality"""
        from src import 2_stream_processor
        
        processor = 2_stream_processor.RealTimeFeatureProcessor()
        current_time = time.time()
        
        # Add events to sliding window
        user_id = 'test_user'
        for i in range(10):
            event_time = current_time - (i * 300)  # Events every 5 minutes
            processor.user_windows[user_id]['events_1h'].append(event_time)
        
        features = processor.calculate_features(user_id, current_time)
        
        # Should only count events within 1 hour
        assert features['events_last_hour'] <= 10

class TestBatchProcessing:
    """Test batch processing and feature engineering"""
    
    def test_feature_engineering(self):
        """Test batch feature engineering"""
        from src import 3_batch_processor
        
        processor = 3_batch_processor.BatchProcessor()
        
        # Create sample data
        events_data = {
            'user_id': ['user_001'] * 100,
            'event_type': ['view'] * 70 + ['cart_add'] * 20 + ['purchase'] * 10,
            'product_id': [f'prod_{i%10}' for i in range(100)],
            'category': ['electronics'] * 100,
            'price': np.random.uniform(10, 500, 100),
            'date': ['2024-01-01'] * 100
        }
        
        transactions_data = {
            'user_id': ['user_001'] * 10,
            'amount': np.random.uniform(20, 1000, 10),
            'fraud_label': [0] * 9 + [1],  # One fraud transaction
            'date': ['2024-01-01'] * 10
        }
        
        events_df = pd.DataFrame(events_data)
        transactions_df = pd.DataFrame(transactions_data)
        
        user_features = processor.create_user_features(events_df, transactions_df)
        
        # Validate feature engineering
        assert len(user_features) == 1  # One user
        assert 'conversion_rate' in user_features.columns
        assert 'fraud_rate' in user_features.columns
        assert user_features.loc['user_001', 'total_purchases'] == 10

class TestMLInference:
    """Test ML inference API"""
    
    @pytest.fixture
    def ml_engine(self):
        """Create ML inference engine for testing"""
        from src import 4_ml_inference_api
        return 4_ml_inference_api.MLInferenceEngine()
    
    @pytest.mark.asyncio
    async def test_feature_caching(self, ml_engine):
        """Test feature caching for performance"""
        user_id = 'test_user_cache'
        
        # First call - should fetch from Redis
        start_time = time.perf_counter()
        features1 = await ml_engine.get_user_features(user_id)
        first_call_time = time.perf_counter() - start_time
        
        # Second call - should use cache
        start_time = time.perf_counter()
        features2 = await ml_engine.get_user_features(user_id)
        second_call_time = time.perf_counter() - start_time
        
        # Cache should be faster
        assert second_call_time < first_call_time
        assert np.array_equal(features1, features2)
    
    @pytest.mark.asyncio
    async def test_fraud_prediction(self, ml_engine):
        """Test fraud prediction functionality"""
        features = np.array([5, 2, 10, 3, 50, 0, 0, 14, 0, 0.3])
        
        fraud_prob, risk_level = await ml_engine.predict_fraud(features, 250.0)
        
        assert 0 <= fraud_prob <= 1
        assert risk_level in ['LOW', 'MEDIUM', 'HIGH']
    
    @pytest.mark.asyncio 
    async def test_inference_latency(self, ml_engine):
        """Test that inference meets <30ms requirement"""
        user_id = 'test_user_latency'
        
        # Warm up cache
        await ml_engine.get_user_features(user_id)
        
        # Test multiple predictions
        latencies = []
        for _ in range(10):
            start_time = time.perf_counter()
            
            features = await ml_engine.get_user_features(user_id)
            fraud_prob, _ = await ml_engine.predict_fraud(features, 100.0)
            rec_score = await ml_engine.predict_recommendation(user_id, 'prod_001')
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            latencies.append(latency_ms)
        
        # Check latency requirements
        avg_latency = np.mean(latencies)
        p99_latency = np.percentile(latencies, 99)
        
        print(f"Average latency: {avg_latency:.2f}ms")
        print(f"P99 latency: {p99_latency:.2f}ms")
        
        # Should meet performance targets
        assert avg_latency < 30, f"Average latency {avg_latency:.2f}ms exceeds 30ms target"
        assert p99_latency < 100, f"P99 latency {p99_latency:.2f}ms exceeds 100ms limit"

class TestEndToEnd:
    """End-to-end integration tests"""
    
    def test_api_health_check(self):
        """Test ML API health endpoint"""
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            assert response.status_code == 200
            
            health_data = response.json()
            assert health_data["status"] == "healthy"
            assert health_data["models_loaded"] is True
            
        except requests.ConnectionError:
            pytest.skip("ML API not running - start with 'python src/4_ml_inference_api.py'")
    
    def test_prediction_endpoint(self):
        """Test full prediction pipeline"""
        try:
            prediction_request = {
                "user_id": "test_user_001",
                "product_id": "prod_001", 
                "transaction_amount": 299.99,
                "context": {"session_id": "test_session"}
            }
            
            response = requests.post(
                "http://localhost:8000/predict",
                json=prediction_request,
                timeout=5
            )
            
            assert response.status_code == 200
            
            result = response.json()
            required_fields = [
                'user_id', 'fraud_probability', 'recommendation_score',
                'risk_level', 'inference_time_ms', 'model_version'
            ]
            
            for field in required_fields:
                assert field in result
            
            # Validate response values
            assert 0 <= result['fraud_probability'] <= 1
            assert result['risk_level'] in ['LOW', 'MEDIUM', 'HIGH']
            assert result['inference_time_ms'] > 0
            
            print(f"✅ Prediction successful - Latency: {result['inference_time_ms']:.2f}ms")
            
        except requests.ConnectionError:
            pytest.skip("ML API not running")

class TestPerformance:
    """Performance and load testing"""
    
    def test_concurrent_predictions(self):
        """Test concurrent prediction handling"""
        try:
            import concurrent.futures
            import requests
            
            def make_prediction(user_id):
                """Make a single prediction request"""
                request_data = {
                    "user_id": f"user_{user_id:04d}",
                    "product_id": "prod_001",
                    "transaction_amount": 150.0
                }
                
                start_time = time.perf_counter()
                response = requests.post(
                    "http://localhost:8000/predict",
                    json=request_data,
                    timeout=10
                )
                latency = (time.perf_counter() - start_time) * 1000
                
                return response.status_code, latency
            
            # Test with 50 concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_prediction, i) for i in range(50)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # Analyze results
            success_count = sum(1 for status, _ in results if status == 200)
            latencies = [latency for status, latency in results if status == 200]
            
            if latencies:
                avg_latency = np.mean(latencies)
                p95_latency = np.percentile(latencies, 95)
                
                print(f"✅ Concurrent test: {success_count}/50 successful")
                print(f"✅ Average latency: {avg_latency:.2f}ms")
                print(f"✅ P95 latency: {p95_latency:.2f}ms")
                
                assert success_count >= 45  # Allow some failures
                assert avg_latency < 50  # Reasonable under load
            
        except requests.ConnectionError:
            pytest.skip("ML API not running")

# Test runner
if __name__ == "__main__":
    # Setup logging
    logger = setup_logging("test_pipeline")
    
    # Run tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--durations=10"
    ])