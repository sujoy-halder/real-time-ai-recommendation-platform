"""
ML Model Training Pipeline
Orchestrates feature engineering, model training, evaluation, and serving
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging
import os
import json
from typing import Dict, Tuple
import joblib
import tensorflow as tf

from advanced_models import (
    FeatureEngineer,
    DeepRecommendationNetwork,
    EmbeddingModel,
    RankingModel,
    TransformerRecommender,
    EnsembleRecommender,
    ModelEvaluator
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ============================================================================
# MODEL TRAINING PIPELINE
# ============================================================================

class ModelTrainingPipeline:
    """Complete ML pipeline for training recommendation models"""
    
    def __init__(self, model_dir: str = '/models'):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        
        self.feature_engineer = FeatureEngineer()
        self.models = {}
        self.metadata = {}
        
    def load_data(self, db_connection) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load data from database"""
        
        logger.info("Loading data from database...")
        
        # Get users
        users_query = """
        SELECT 
            u.id,
            u.created_at,
            COUNT(DISTINCT ui.id) as total_watches,
            AVG(ui.rating) as avg_rating,
            COUNT(DISTINCT CASE WHEN ui.interaction_type = 'like' THEN ui.id END) as total_likes
        FROM users u
        LEFT JOIN user_interactions ui ON u.id = ui.user_id
        GROUP BY u.id, u.created_at
        """
        users_df = pd.read_sql(users_query, db_connection)
        logger.info(f"Loaded {len(users_df)} users")
        
        # Get content
        content_query = """
        SELECT 
            c.id,
            c.duration,
            c.rating,
            c.release_date,
            c.genre,
            COUNT(DISTINCT ui.id) as total_views,
            COUNT(DISTINCT CASE WHEN ui.rating IS NOT NULL THEN ui.id END) as rating_count,
            AVG(ui.rating) as avg_rating
        FROM content c
        LEFT JOIN user_interactions ui ON c.id = ui.content_id
        GROUP BY c.id, c.duration, c.rating, c.release_date, c.genre
        """
        content_df = pd.read_sql(content_query, db_connection)
        logger.info(f"Loaded {len(content_df)} content items")
        
        # Get interactions
        interactions_query = """
        SELECT 
            user_id,
            content_id,
            interaction_type,
            rating,
            watch_time,
            timestamp
        FROM user_interactions
        WHERE timestamp >= NOW() - INTERVAL '90 days'
        ORDER BY timestamp
        """
        interactions_df = pd.read_sql(interactions_query, db_connection)
        logger.info(f"Loaded {len(interactions_df)} interactions")
        
        return users_df, content_df, interactions_df
    
    def engineer_features(self, users_df: pd.DataFrame, 
                         content_df: pd.DataFrame, 
                         interactions_df: pd.DataFrame):
        """Engineer features"""
        
        logger.info("Engineering features...")
        
        user_features = self.feature_engineer.engineer_user_features(users_df)
        content_features = self.feature_engineer.engineer_content_features(content_df)
        
        # Prepare training data
        X_user = []
        X_item = []
        y = []
        
        for _, row in interactions_df.iterrows():
            user_id = int(row['user_id'])
            item_id = int(row['content_id'])
            rating = float(row['rating']) if pd.notna(row['rating']) else 3.0
            
            if user_id < len(user_features) and item_id < len(content_features):
                X_user.append(user_features[user_id])
                X_item.append(content_features[item_id])
                y.append(rating / 5.0)  # Normalize to 0-1
        
        X_user = np.array(X_user)
        X_item = np.array(X_item)
        y = np.array(y)
        
        logger.info(f"Engineered features: user_shape={X_user.shape}, item_shape={X_item.shape}, y_shape={y.shape}")
        
        return X_user, X_item, y, user_features, content_features
    
    def train_deep_network(self, X_user: np.ndarray, X_item: np.ndarray, 
                          y: np.ndarray, num_epochs: int = 10):
        """Train deep neural network"""
        
        logger.info("Training deep recommendation network...")
        
        dnn_model = DeepRecommendationNetwork(
            user_feature_dim=X_user.shape[1],
            item_feature_dim=X_item.shape[1],
            hidden_dims=[256, 128, 64]
        )
        dnn_model.build()
        
        history = dnn_model.train(X_user, X_item, y, epochs=num_epochs, batch_size=32)
        
        self.models['deep_network'] = dnn_model
        logger.info("Deep network training completed")
        
        return history
    
    def train_embedding_model(self, interactions_df: pd.DataFrame, 
                             num_users: int, num_items: int, num_epochs: int = 10):
        """Train embedding model"""
        
        logger.info("Training embedding model...")
        
        # Prepare embedding training data
        user_ids = interactions_df['user_id'].values.astype(np.int32)
        item_ids = interactions_df['content_id'].values.astype(np.int32)
        ratings = interactions_df['rating'].fillna(3.0).values.astype(np.float32) / 5.0
        
        # Build model
        embedding_model = EmbeddingModel(num_users, num_items, embedding_dim=32)
        
        # Compile
        embedding_model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.01),
            loss='mse',
            metrics=['mae']
        )
        
        # Train
        embedding_model.fit(
            [user_ids, item_ids],
            ratings,
            epochs=num_epochs,
            batch_size=64,
            validation_split=0.2,
            callbacks=[
                tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=3)
            ],
            verbose=1
        )
        
        self.models['embedding_model'] = embedding_model
        logger.info("Embedding model training completed")
        
        return embedding_model
    
    def train_transformer_model(self, interactions_df: pd.DataFrame, 
                               num_items: int, num_epochs: int = 10):
        """Train transformer model for sequential recommendations"""
        
        logger.info("Training transformer model...")
        
        # Create sequences
        sequences = []
        max_seq_length = 50
        
        for user_id in interactions_df['user_id'].unique():
            user_interactions = interactions_df[interactions_df['user_id'] == user_id].sort_values('timestamp')
            seq = user_interactions['content_id'].values[:max_seq_length]
            
            # Pad or truncate
            if len(seq) < max_seq_length:
                seq = np.pad(seq, (max_seq_length - len(seq), 0), 'constant', constant_values=0)
            else:
                seq = seq[-max_seq_length:]
            
            sequences.append(seq)
        
        sequences = np.array(sequences)
        
        # Build and train transformer
        transformer = TransformerRecommender(embedding_dim=32, num_heads=4, 
                                           num_layers=2, max_seq_length=max_seq_length)
        transformer.build(num_items)
        
        # Train (predict next item in sequence)
        X = sequences[:, :-1]
        y = sequences[:, -1]
        
        transformer.model.fit(
            X, y,
            epochs=num_epochs,
            batch_size=32,
            validation_split=0.2,
            callbacks=[
                tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=3)
            ],
            verbose=1
        )
        
        self.models['transformer'] = transformer
        logger.info("Transformer model training completed")
        
        return transformer
    
    def train_ranking_model(self, X_user: np.ndarray, X_item: np.ndarray, 
                           y: np.ndarray, interactions_df: pd.DataFrame):
        """Train ranking model"""
        
        logger.info("Training ranking model...")
        
        # Combine features
        X = np.concatenate([X_user, X_item], axis=1)
        
        # Get group sizes (items per user)
        groups = interactions_df.groupby('user_id').size().values
        
        ranking_model = RankingModel()
        ranking_model.train(X, y, groups=groups.tolist())
        
        self.models['ranking'] = ranking_model
        logger.info("Ranking model training completed")
        
        return ranking_model
    
    def create_ensemble(self):
        """Create ensemble model"""
        
        logger.info("Creating ensemble model...")
        
        ensemble = EnsembleRecommender()
        
        # Add models with weights
        if 'deep_network' in self.models:
            ensemble.add_model('deep_network', self.models['deep_network'], weight=0.4)
        
        if 'embedding_model' in self.models:
            ensemble.add_model('embedding_model', self.models['embedding_model'], weight=0.3)
        
        if 'ranking' in self.models:
            ensemble.add_model('ranking', self.models['ranking'], weight=0.3)
        
        self.models['ensemble'] = ensemble
        logger.info("Ensemble model created successfully")
        
        return ensemble
    
    def evaluate_models(self, X_user: np.ndarray, X_item: np.ndarray, 
                       y: np.ndarray) -> Dict:
        """Evaluate all models"""
        
        logger.info("Evaluating models...")
        
        evaluator = ModelEvaluator()
        results = {}
        
        for name, model in self.models.items():
            try:
                if name == 'deep_network':
                    predictions = model.predict(X_user, X_item)
                    mse = np.mean((predictions.flatten() - y) ** 2)
                    mae = np.mean(np.abs(predictions.flatten() - y))
                    results[name] = {'mse': float(mse), 'mae': float(mae)}
                
                elif name == 'ensemble':
                    predictions = model.predict(X_user, X_item)
                    mse = np.mean((predictions.flatten() - y) ** 2)
                    mae = np.mean(np.abs(predictions.flatten() - y))
                    results[name] = {'mse': float(mse), 'mae': float(mae)}
                
                logger.info(f"{name}: MSE={results[name].get('mse', 'N/A')}, MAE={results[name].get('mae', 'N/A')}")
            
            except Exception as e:
                logger.error(f"Error evaluating {name}: {e}")
        
        return results
    
    def save_models(self):
        """Save trained models"""
        
        logger.info("Saving models...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for name, model in self.models.items():
            model_path = os.path.join(self.model_dir, f'{name}_{timestamp}.pkl')
            
            try:
                if hasattr(model, 'save'):
                    model.save(model_path)
                else:
                    joblib.dump(model, model_path)
                
                logger.info(f"Saved {name} to {model_path}")
            except Exception as e:
                logger.error(f"Error saving {name}: {e}")
        
        # Save metadata
        self.metadata = {
            'timestamp': timestamp,
            'models': list(self.models.keys()),
            'feature_names': self.feature_engineer.feature_names
        }
        
        metadata_path = os.path.join(self.model_dir, f'metadata_{timestamp}.json')
        with open(metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        
        logger.info(f"Saved metadata to {metadata_path}")
    
    def run_full_pipeline(self, db_connection):
        """Run complete training pipeline"""
        
        logger.info("="*60)
        logger.info("Starting ML Model Training Pipeline")
        logger.info("="*60)
        
        # Load data
        users_df, content_df, interactions_df = self.load_data(db_connection)
        
        # Engineer features
        X_user, X_item, y, user_features, content_features = self.engineer_features(
            users_df, content_df, interactions_df
        )
        
        # Train models
        self.train_deep_network(X_user, X_item, y, num_epochs=10)
        self.train_embedding_model(interactions_df, len(user_features), len(content_features), num_epochs=10)
        self.train_transformer_model(interactions_df, len(content_features), num_epochs=10)
        self.train_ranking_model(X_user, X_item, y, interactions_df)
        
        # Create ensemble
        self.create_ensemble()
        
        # Evaluate
        results = self.evaluate_models(X_user, X_item, y)
        
        # Save models
        self.save_models()
        
        logger.info("="*60)
        logger.info("ML Model Training Pipeline Completed Successfully!")
        logger.info("="*60)
        
        return results


if __name__ == '__main__':
    # Example usage
    logger.info("ML Model Training Pipeline Ready")
