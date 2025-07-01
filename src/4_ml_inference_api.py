#!/usr/bin/env python3
"""
Ultra-fast ML inference API with <30ms latency
Demonstrates: Model serving, performance optimization, caching
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
import pandas as pd
import joblib
import redis
import time
import asyncio
from typing import Dict, Optional
import logging
from utils import SmartCache
from datetime import datetime, timedelta

app = FastAPI(title="Real-time ML Inference", version="1.0.0")

class PredictionRequest(BaseModel):
    user_id: str
    product_id: Optional[str] = None
    transaction_amount: Optional[float] = None
    context: Dict = {}

class PredictionResponse(BaseModel):
    user_id: str
    fraud_probability: float
    recommendation_score: float
    risk_level: str
    inference_time_ms: float
    model_version: str

class MLInferenceEngine:
    def __init__(self):
        # Initialize models (in production, load from model registry)
        self.fraud_model = self.create_fraud_model()
        self.recommendation_model = self.create_recommendation_model()
        
        # Redis for ultra-fast feature lookup
        # self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.cache = SmartCache()
        
        # In-memory feature cache for <30ms latency
        self.feature_cache = {}
        self.model_cache = {}
        self.cache_ttl = 30  # 30 second TTL
        
        print("🤖 ML Inference Engine initialized")
    
    def create_fraud_model(self):
        """Create a simple but effective fraud detection model"""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler
        
        # In production, load from model registry
        # For demo, create a trained model
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        
        # Simulate training data
        X_train = np.random.random((1000, 10))
        y_train = np.random.choice([0, 1], 1000, p=[0.95, 0.05])
        
        model.fit(X_train, y_train)
        
        return {
            'model': model,
            'scaler': StandardScaler().fit(X_train),
            'version': '1.0.0',
            'features': [
                'events_last_hour', 'purchases_last_24h', 'session_length',
                'transaction_amount', 'avg_transaction', 'rapid_activity',
                'burst_purchases', 'hour_of_day', 'is_weekend', 'risk_score'
            ]
        }
    
    def create_recommendation_model(self):
        """Create a simple recommendation model"""
        # Simple collaborative filtering simulation
        return {
            'user_embeddings': np.random.random((1000, 50)),
            'product_embeddings': np.random.random((200, 50)),
            'version': '1.0.0'
        }
    

    async def get_user_features(self, user_id: str) -> np.ndarray:
        """Get user features with smart caching for <30ms response"""
        cache_key = f"features:{user_id}"
        
        # L1 Cache: In-memory (fastest)
        if cache_key in self.feature_cache:
            cached_time, features = self.feature_cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return features
        
        # L2 Cache: Smart cache (Redis or memory)
        try:
            cached_features = self.cache.hgetall(f"features:{user_id}")
            if cached_features:
                features = np.array([
                    float(cached_features.get('events_last_hour', 0)),
                    float(cached_features.get('purchases_last_24h', 0)),
                    float(cached_features.get('session_length', 0)),
                    float(cached_features.get('categories_in_session', 0)),
                    float(cached_features.get('avg_events_per_hour', 0)),
                    float(cached_features.get('rapid_activity', 0)),
                    float(cached_features.get('burst_purchases', 0)),
                    float(cached_features.get('hour_of_day', 12)),
                    float(cached_features.get('is_weekend', 0)),
                    0.5  # Default risk score
                ])
            else:
                # Fallback: Compute basic features
                features = self._compute_basic_features(user_id)
            
            # Cache for next request
            self.feature_cache[cache_key] = (time.time(), features)
            return features
            
        except Exception as e:
            # Ultimate fallback
            logging.warning(f"Feature retrieval failed: {e}")
            return self._compute_basic_features(user_id)

    def _compute_basic_features(self, user_id: str) -> np.ndarray:
        """Compute basic features without external dependencies"""
        import hashlib
        
        # Generate consistent features based on user_id
        user_hash = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)
        np.random.seed(user_hash % (2**31))
        
        # Simulate realistic feature values
        base_features = np.random.beta(2, 5, 8) * 10  # Realistic skewed distribution
        current_hour = datetime.now().hour
        is_weekend = int(datetime.now().weekday() >= 5)
        
        features = np.append(base_features, [current_hour, is_weekend])
        return features
    
    # async def get_user_features(self, user_id: str) -> np.ndarray:
    #     """Get user features with aggressive caching for <30ms response"""
    #     cache_key = f"features:{user_id}"
        
    #     # L1 Cache: In-memory (fastest)
    #     if cache_key in self.feature_cache:
    #         cached_time, features = self.feature_cache[cache_key]
    #         if time.time() - cached_time < self.cache_ttl:
    #             return features
        
    #     # L2 Cache: Redis (fast)
    #     try:
    #         redis_features = self.redis_client.hgetall(f"features:{user_id}")
    #         if redis_features:
    #             features = np.array([
    #                 float(redis_features.get('events_last_hour', 0)),
    #                 float(redis_features.get('purchases_last_24h', 0)),
    #                 float(redis_features.get('session_length', 0)),
    #                 float(redis_features.get('categories_in_session', 0)),
    #                 float(redis_features.get('avg_events_per_hour', 0)),
    #                 float(redis_features.get('rapid_activity', 0)),
    #                 float(redis_features.get('burst_purchases', 0)),
    #                 float(redis_features.get('hour_of_day', 12)),
    #                 float(redis_features.get('is_weekend', 0)),
    #                 0.5  # Default risk score
    #             ])
    #         else:
    #             # Fallback: Default feature vector
    #             features = np.array([0, 0, 0, 0, 0, 0, 0, 12, 0, 0.5])
            
    #         # Cache for next request
    #         self.feature_cache[cache_key] = (time.time(), features)
    #         return features
            
    #     except Exception:
    #         # Ultimate fallback
    #         return np.array([0, 0, 0, 0, 0, 0, 0, 12, 0, 0.5])
    
    async def predict_fraud(self, features: np.ndarray, transaction_amount: float) -> tuple:
        """Ultra-fast fraud prediction"""
        try:
            # Add transaction amount to features
            enhanced_features = np.append(features, transaction_amount)
            
            # Scale features
            scaled_features = self.fraud_model['scaler'].transform(
                enhanced_features.reshape(1, -1)
            )
            
            # Predict
            fraud_prob = self.fraud_model['model'].predict_proba(scaled_features)[0][1]
            
            # Risk level
            if fraud_prob > 0.8:
                risk_level = "HIGH"
            elif fraud_prob > 0.5:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            return float(fraud_prob), risk_level
            
        except Exception:
            return 0.1, "LOW"  # Safe default
    
    async def predict_recommendation(self, user_id: str, product_id: str) -> float:
        """Ultra-fast recommendation scoring"""
        try:
            # Simple embedding-based similarity
            user_idx = hash(user_id) % 1000
            product_idx = hash(product_id) % 200
            
            user_emb = self.recommendation_model['user_embeddings'][user_idx]
            product_emb = self.recommendation_model['product_embeddings'][product_idx]
            
            # Cosine similarity
            score = np.dot(user_emb, product_emb) / (
                np.linalg.norm(user_emb) * np.linalg.norm(product_emb)
            )
            
            return float(score)
            
        except Exception:
            return 0.5  # Default score

# Initialize ML engine
ml_engine = MLInferenceEngine()

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Main prediction endpoint - target <30ms latency"""
    start_time = time.perf_counter()
    
    try:
        # Get user features (cached for speed)
        features = await ml_engine.get_user_features(request.user_id)
        
        # Run predictions in parallel
        fraud_task = ml_engine.predict_fraud(
            features, 
            request.transaction_amount or 100.0
        )
        
        rec_task = ml_engine.predict_recommendation(
            request.user_id,
            request.product_id or "prod_001"
        )
        
        # Await both predictions
        (fraud_prob, risk_level), rec_score = await asyncio.gather(
            fraud_task, rec_task
        )
        
        inference_time_ms = (time.perf_counter() - start_time) * 1000
        
        return PredictionResponse(
            user_id=request.user_id,
            fraud_probability=fraud_prob,
            recommendation_score=rec_score,
            risk_level=risk_level,
            inference_time_ms=round(inference_time_ms, 2),
            model_version="1.0.0"
        )
        
    except Exception as e:
        logging.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "models_loaded": True,
        "cache_size": len(ml_engine.feature_cache),
        "timestamp": time.time()
    }

@app.get("/metrics")
async def get_metrics():
    """Performance metrics"""
    return {
        "feature_cache_size": len(ml_engine.feature_cache),
        "model_version": ml_engine.fraud_model['version'],
        "cache_ttl": ml_engine.cache_ttl
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)