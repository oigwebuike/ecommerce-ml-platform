#!/usr/bin/env python3
"""
Batch processing for historical analytics and feature engineering
Demonstrates: Large-scale data processing, feature engineering, data quality
"""

import pandas as pd
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging

class BatchProcessor:
    def __init__(self):
        self.data_path = Path("sample_data")
        self.output_path = Path("processed_data")
        self.output_path.mkdir(exist_ok=True)
        
    def simulate_spark_processing(self, df, operation_name):
        """Simulate Spark distributed processing with pandas"""
        print(f"🔄 Processing {len(df)} records - {operation_name}")
        time.sleep(0.1)  # Simulate processing time
        return df
    
    def load_historical_data(self) -> tuple:
        """Load historical events and transactions"""
        # In real implementation, this would read from S3/HDFS
        # For demo, generate sample data
        
        events_data = []
        transactions_data = []
        
        # Generate 30 days of historical data
        for day in range(30):
            date = datetime.now() - timedelta(days=day)
            
            # Generate daily events
            for _ in range(1000):  # 1000 events per day
                events_data.append({
                    'user_id': f"user_{np.random.randint(1, 1001):04d}",
                    'event_type': np.random.choice(['view', 'cart_add', 'purchase'], p=[0.7, 0.2, 0.1]),
                    'product_id': f"prod_{np.random.randint(1, 201):03d}",
                    'category': np.random.choice(['electronics', 'clothing', 'books']),
                    'price': round(np.random.uniform(10, 500), 2),
                    'timestamp': date.isoformat(),
                    'date': date.strftime('%Y-%m-%d')
                })
            
            # Generate daily transactions
            for _ in range(100):  # 100 transactions per day
                transactions_data.append({
                    'user_id': f"user_{np.random.randint(1, 1001):04d}",
                    'amount': round(np.random.uniform(20, 1000), 2),
                    'timestamp': date.isoformat(),
                    'date': date.strftime('%Y-%m-%d'),
                    'fraud_label': np.random.choice([0, 1], p=[0.95, 0.05])  # 5% fraud
                })
        
        return pd.DataFrame(events_data), pd.DataFrame(transactions_data)
    
    def create_user_features(self, events_df, transactions_df):
        """Create comprehensive user features for ML training"""
        print("🏗️  Building user features...")
        
        # User behavior aggregations (simulate Spark groupBy)
        user_behavior = self.simulate_spark_processing(
            events_df.groupby('user_id').agg({
                'event_type': ['count', lambda x: (x == 'purchase').sum()],
                'product_id': 'nunique',
                'category': 'nunique',
                'price': ['mean', 'sum', 'max'],
                'date': 'nunique'
            }).round(2), 
            "User Behavior Aggregation"
        )
        
        # Flatten column names
        user_behavior.columns = [
            'total_events', 'total_purchases', 'unique_products', 
            'unique_categories', 'avg_price', 'total_spent', 
            'max_price', 'active_days'
        ]
        
        # Transaction features
        user_transactions = self.simulate_spark_processing(
            transactions_df.groupby('user_id').agg({
                'amount': ['count', 'mean', 'std', 'max'],
                'fraud_label': 'sum'
            }).round(2),
            "Transaction Features"
        )
        
        user_transactions.columns = [
            'transaction_count', 'avg_transaction', 'transaction_std', 
            'max_transaction', 'fraud_count'
        ]
        
        # Combine features
        user_features = user_behavior.join(user_transactions, how='outer').fillna(0)
        
        # Add derived features
        user_features['conversion_rate'] = (
            user_features['total_purchases'] / user_features['total_events']
        ).fillna(0)
        
        user_features['fraud_rate'] = (
            user_features['fraud_count'] / user_features['transaction_count']
        ).fillna(0)
        
        user_features['avg_events_per_day'] = (
            user_features['total_events'] / user_features['active_days']
        ).fillna(0)
        
        return user_features
    
    def create_product_features(self, events_df):
        """Create product-level features"""
        print("📦 Building product features...")
        
        product_features = self.simulate_spark_processing(
            events_df.groupby(['product_id', 'category']).agg({
                'user_id': 'nunique',
                'event_type': ['count', lambda x: (x == 'purchase').sum()],
                'price': 'mean'
            }).round(2),
            "Product Features"
        )
        
        product_features.columns = ['unique_users', 'total_views', 'purchases', 'avg_price']
        product_features['conversion_rate'] = (
            product_features['purchases'] / product_features['total_views']
        ).fillna(0)
        
        return product_features
    
    def run_feature_pipeline(self):
        """Main batch processing pipeline"""
        print("🚀 Starting batch feature engineering pipeline...")
        
        # Load data (simulate reading from data lake)
        events_df, transactions_df = self.load_historical_data()
        
        print(f"📊 Loaded {len(events_df)} events and {len(transactions_df)} transactions")
        
        # Data quality checks
        self.data_quality_checks(events_df, transactions_df)
        
        # Feature engineering
        user_features = self.create_user_features(events_df, transactions_df)
        product_features = self.create_product_features(events_df)
        
        # Save features (simulate writing to feature store)
        user_features.to_parquet(self.output_path / "user_features.parquet")
        product_features.to_parquet(self.output_path / "product_features.parquet")
        
        print(f"✅ Feature pipeline complete! Created {len(user_features)} user features")
        return user_features, product_features
    
    def data_quality_checks(self, events_df, transactions_df):
        """Data quality validation"""
        print("🔍 Running data quality checks...")
        
        # Check for nulls
        events_nulls = events_df.isnull().sum()
        if events_nulls.any():
            print(f"⚠️  Found nulls in events: {events_nulls[events_nulls > 0].to_dict()}")
        
        # Check for duplicates
        duplicates = events_df.duplicated().sum()
        if duplicates > 0:
            print(f"⚠️  Found {duplicates} duplicate events")
        
        # Check value ranges
        invalid_prices = (events_df['price'] <= 0).sum()
        if invalid_prices > 0:
            print(f"⚠️  Found {invalid_prices} invalid prices")
        
        print("✅ Data quality checks complete")

if __name__ == "__main__":
    import numpy as np  # Import here to avoid issues
    
    processor = BatchProcessor()
    user_features, product_features = processor.run_feature_pipeline()
    
    print("\n📈 Sample User Features:")
    print(user_features.head())