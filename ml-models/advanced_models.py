"""
Advanced Machine Learning Models for Recommendation System
Includes: Deep Learning, Embedding Models, Ranking Models, Feature Engineering
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder
from sklearn.decomposition import PCA
import logging
from typing import Tuple, List, Dict
import joblib

logger = logging.getLogger(__name__)

# ============================================================================
# 1. FEATURE ENGINEERING
# ============================================================================

class FeatureEngineer:
    """Extract and engineer features from raw data"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_names = []
        
    def engineer_user_features(self, user_df: pd.DataFrame) -> np.ndarray:
        """Engineer features from user data"""
        features = pd.DataFrame()
        
        # User demographics
        if 'age' in user_df.columns:
            features['age'] = user_df['age']
            features['age_group'] = pd.cut(user_df['age'], bins=[0, 18, 25, 35, 50, 100])
        
        # Engagement metrics
        if 'total_watches' in user_df.columns:
            features['total_watches'] = user_df['total_watches']
            features['log_watches'] = np.log1p(user_df['total_watches'])
        
        if 'avg_rating' in user_df.columns:
            features['avg_rating'] = user_df['avg_rating']
        
        if 'watch_frequency' in user_df.columns:
            features['watch_frequency'] = user_df['watch_frequency']
        
        # User account age (days since registration)
        if 'created_at' in user_df.columns:
            features['account_age'] = (pd.Timestamp.now() - pd.to_datetime(user_df['created_at'])).dt.days
        
        # Encode categorical features
        if 'country' in user_df.columns:
            le = LabelEncoder()
            features['country_encoded'] = le.fit_transform(user_df['country'])
            self.label_encoders['country'] = le
        
        self.feature_names = features.columns.tolist()
        return self.scaler.fit_transform(features)
    
    def engineer_content_features(self, content_df: pd.DataFrame) -> np.ndarray:
        """Engineer features from content data"""
        features = pd.DataFrame()
        
        # Content metadata
        if 'duration' in content_df.columns:
            features['duration'] = content_df['duration']
            features['log_duration'] = np.log1p(content_df['duration'])
        
        if 'rating' in content_df.columns:
            features['rating'] = content_df['rating']
        
        # Genre encoding (one-hot)
        if 'genre' in content_df.columns:
            genre_dummies = pd.get_dummies(content_df['genre'], prefix='genre')
            features = pd.concat([features, genre_dummies], axis=1)
        
        # Content age (days since release)
        if 'release_date' in content_df.columns:
            features['content_age'] = (pd.Timestamp.now() - pd.to_datetime(content_df['release_date'])).dt.days
        
        # Popularity metrics
        if 'total_views' in content_df.columns:
            features['total_views'] = content_df['total_views']
            features['log_views'] = np.log1p(content_df['total_views'])
        
        if 'avg_rating_count' in content_df.columns:
            features['rating_count'] = content_df['avg_rating_count']
        
        features = features.fillna(0)
        self.feature_names = features.columns.tolist()
        return self.scaler.fit_transform(features)
    
    def engineer_interaction_features(self, interaction_df: pd.DataFrame) -> np.ndarray:
        """Engineer features from user-item interactions"""
        features = pd.DataFrame()
        
        # Interaction type
        if 'interaction_type' in interaction_df.columns:
            interaction_dummies = pd.get_dummies(interaction_df['interaction_type'], prefix='interaction')
            features = pd.concat([features, interaction_dummies], axis=1)
        
        # Watch time ratio
        if 'watch_time' in interaction_df.columns and 'duration' in interaction_df.columns:
            features['watch_ratio'] = interaction_df['watch_time'] / (interaction_df['duration'] + 1)
        
        # Time since interaction
        if 'timestamp' in interaction_df.columns:
            features['time_since'] = (pd.Timestamp.now() - pd.to_datetime(interaction_df['timestamp'])).dt.days
        
        # Rating
        if 'rating' in interaction_df.columns:
            features['rating'] = interaction_df['rating']
        
        features = features.fillna(0)
        return self.scaler.fit_transform(features)


# ============================================================================
# 2. EMBEDDING MODELS
# ============================================================================

class EmbeddingModel(keras.Model):
    """Learn user and item embeddings"""
    
    def __init__(self, num_users: int, num_items: int, embedding_dim: int = 32):
        super(EmbeddingModel, self).__init__()
        
        self.user_embedding = layers.Embedding(num_users, embedding_dim, name='user_embedding')
        self.item_embedding = layers.Embedding(num_items, embedding_dim, name='item_embedding')
        
        self.user_bias = layers.Embedding(num_users, 1, name='user_bias')
        self.item_bias = layers.Embedding(num_items, 1, name='item_bias')
    
    def call(self, inputs):
        user_input, item_input = inputs
        
        user_vec = self.user_embedding(user_input)
        item_vec = self.item_embedding(item_input)
        
        user_b = self.user_bias(user_input)
        item_b = self.item_bias(item_input)
        
        # Dot product + bias
        dot_product = tf.reduce_sum(user_vec * item_vec, axis=1, keepdims=True)
        output = dot_product + user_b + item_b
        
        return output


# ============================================================================
# 3. DEEP NEURAL NETWORK FOR RECOMMENDATIONS
# ============================================================================

class DeepRecommendationNetwork:
    """Deep neural network for recommendation prediction"""
    
    def __init__(self, user_feature_dim: int, item_feature_dim: int, 
                 hidden_dims: List[int] = [256, 128, 64]):
        self.user_feature_dim = user_feature_dim
        self.item_feature_dim = item_feature_dim
        self.hidden_dims = hidden_dims
        self.model = None
        
    def build(self):
        """Build the neural network architecture"""
        
        # User feature input
        user_input = keras.Input(shape=(self.user_feature_dim,), name='user_features')
        
        # Item feature input
        item_input = keras.Input(shape=(self.item_feature_dim,), name='item_features')
        
        # User tower
        x_user = user_input
        for dim in self.hidden_dims:
            x_user = layers.Dense(dim, activation='relu')(x_user)
            x_user = layers.BatchNormalization()(x_user)
            x_user = layers.Dropout(0.3)(x_user)
        
        user_output = layers.Dense(32, activation='relu', name='user_embedding')(x_user)
        
        # Item tower
        x_item = item_input
        for dim in self.hidden_dims:
            x_item = layers.Dense(dim, activation='relu')(x_item)
            x_item = layers.BatchNormalization()(x_item)
            x_item = layers.Dropout(0.3)(x_item)
        
        item_output = layers.Dense(32, activation='relu', name='item_embedding')(x_item)
        
        # Interaction (dot product)
        interaction = layers.Dot(axes=1, name='interaction')([user_output, item_output])
        
        # Dense layers for ranking
        x = layers.Concatenate()([user_output, item_output, interaction])
        x = layers.Dense(128, activation='relu')(x)
        x = layers.Dropout(0.2)(x)
        x = layers.Dense(64, activation='relu')(x)
        x = layers.Dropout(0.2)(x)
        
        # Output layer
        output = layers.Dense(1, activation='sigmoid', name='rating_prediction')(x)
        
        # Create model
        self.model = keras.Model(inputs=[user_input, item_input], outputs=output)
        
        # Compile
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        logger.info("Deep recommendation network built successfully")
        return self.model
    
    def train(self, X_user: np.ndarray, X_item: np.ndarray, y: np.ndarray, 
              epochs: int = 10, batch_size: int = 32, validation_split: float = 0.2):
        """Train the model"""
        
        history = self.model.fit(
            [X_user, X_item],
            y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            callbacks=[
                keras.callbacks.EarlyStopping(monitor='val_loss', patience=3, restore_best_weights=True),
                keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=2)
            ],
            verbose=1
        )
        
        return history
    
    def predict(self, X_user: np.ndarray, X_item: np.ndarray) -> np.ndarray:
        """Make predictions"""
        return self.model.predict([X_user, X_item])


# ============================================================================
# 4. RANKING MODEL (LightGBM)
# ============================================================================

class RankingModel:
    """Ranking model for learning-to-rank"""
    
    def __init__(self):
        try:
            import lightgbm as lgb
            self.lgb = lgb
            self.model = None
        except ImportError:
            logger.warning("LightGBM not installed, using alternative ranking")
            from sklearn.ensemble import GradientBoostingRegressor
            self.model = GradientBoostingRegressor()
    
    def train(self, X: np.ndarray, y: np.ndarray, groups: List[int] = None):
        """Train ranking model"""
        
        if self.lgb and groups:
            # LambdaMART ranking
            train_data = self.lgb.Dataset(X, label=y, group=groups)
            
            params = {
                'objective': 'rank_xendcg',
                'metric': 'ndcg',
                'num_leaves': 31,
                'learning_rate': 0.05
            }
            
            self.model = self.lgb.train(params, train_data, num_boost_round=100)
        else:
            self.model.fit(X, y)
        
        logger.info("Ranking model trained")
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict rankings"""
        if self.lgb:
            return self.model.predict(X)
        else:
            return self.model.predict(X)


# ============================================================================
# 5. TRANSFORMER MODEL (ATTENTION-BASED)
# ============================================================================

class TransformerRecommender:
    """Transformer-based model for sequential recommendations"""
    
    def __init__(self, embedding_dim: int = 32, num_heads: int = 4, 
                 num_layers: int = 2, max_seq_length: int = 50):
        
        self.embedding_dim = embedding_dim
        self.num_heads = num_heads
        self.num_layers = num_layers
        self.max_seq_length = max_seq_length
        self.model = None
    
    def build(self, num_items: int):
        """Build transformer model"""
        
        # Input: sequence of item IDs
        item_input = keras.Input(shape=(self.max_seq_length,), dtype='int32', name='item_sequence')
        
        # Embedding layer
        x = layers.Embedding(num_items, self.embedding_dim)(item_input)
        
        # Positional encoding
        x = x + self._positional_encoding(self.max_seq_length, self.embedding_dim)
        
        # Transformer blocks
        for _ in range(self.num_layers):
            # Multi-head attention
            attention_output = layers.MultiHeadAttention(
                num_heads=self.num_heads,
                key_dim=self.embedding_dim // self.num_heads
            )(x, x)
            
            x = layers.Add()([x, attention_output])
            x = layers.LayerNormalization(epsilon=1e-6)(x)
            
            # Feed forward
            ff_output = layers.Dense(self.embedding_dim * 4, activation='relu')(x)
            ff_output = layers.Dense(self.embedding_dim)(ff_output)
            
            x = layers.Add()([x, ff_output])
            x = layers.LayerNormalization(epsilon=1e-6)(x)
        
        # Global average pooling
        x = layers.GlobalAveragePooling1D()(x)
        
        # Output layer
        output = layers.Dense(num_items, activation='softmax', name='predictions')(x)
        
        self.model = keras.Model(inputs=item_input, outputs=output)
        self.model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        logger.info("Transformer recommender built successfully")
        return self.model
    
    def _positional_encoding(self, length: int, depth: int) -> np.ndarray:
        """Create positional encoding"""
        depth = depth / 2
        positions = np.arange(length)[:, np.newaxis]
        depths = np.arange(depth)[np.newaxis, :] / depth
        angle_rates = 1 / (10000 ** depths)
        angle_rads = positions * angle_rates
        pos_encoding = np.concatenate([np.sin(angle_rads), np.cos(angle_rads)], axis=-1)
        return tf.cast(pos_encoding[np.newaxis, ...], dtype=tf.float32)


# ============================================================================
# 6. ENSEMBLE MODEL
# ============================================================================

class EnsembleRecommender:
    """Ensemble of multiple models"""
    
    def __init__(self):
        self.models = {}
        self.weights = {}
    
    def add_model(self, name: str, model, weight: float = 1.0):
        """Add a model to ensemble"""
        self.models[name] = model
        self.weights[name] = weight
    
    def predict(self, *args, **kwargs) -> np.ndarray:
        """Ensemble prediction"""
        
        predictions = {}
        total_weight = sum(self.weights.values())
        
        for name, model in self.models.items():
            pred = model.predict(*args, **kwargs)
            predictions[name] = pred
        
        # Weighted average
        ensemble_pred = np.zeros_like(list(predictions.values())[0])
        for name, pred in predictions.items():
            ensemble_pred += (self.weights[name] / total_weight) * pred
        
        return ensemble_pred
    
    def save(self, path: str):
        """Save ensemble"""
        joblib.dump({
            'models': self.models,
            'weights': self.weights
        }, path)
    
    def load(self, path: str):
        """Load ensemble"""
        data = joblib.load(path)
        self.models = data['models']
        self.weights = data['weights']


# ============================================================================
# 7. MODEL EVALUATION
# ============================================================================

class ModelEvaluator:
    """Evaluate recommendation models"""
    
    @staticmethod
    def ndcg(predictions: np.ndarray, ground_truth: np.ndarray, k: int = 10) -> float:
        """Normalized Discounted Cumulative Gain"""
        
        # Get top-k indices
        top_k_indices = np.argsort(-predictions)[:k]
        
        # Calculate DCG
        dcg = 0
        for i, idx in enumerate(top_k_indices):
            if idx < len(ground_truth) and ground_truth[idx] == 1:
                dcg += 1 / np.log2(i + 2)
        
        # Calculate IDCG (ideal DCG)
        idcg = sum([1 / np.log2(i + 2) for i in range(min(k, np.sum(ground_truth)))])
        
        return dcg / idcg if idcg > 0 else 0
    
    @staticmethod
    def recall_at_k(predictions: np.ndarray, ground_truth: np.ndarray, k: int = 10) -> float:
        """Recall@k metric"""
        
        top_k_indices = np.argsort(-predictions)[:k]
        hits = sum([1 for idx in top_k_indices if idx < len(ground_truth) and ground_truth[idx] == 1])
        
        return hits / np.sum(ground_truth) if np.sum(ground_truth) > 0 else 0
    
    @staticmethod
    def precision_at_k(predictions: np.ndarray, ground_truth: np.ndarray, k: int = 10) -> float:
        """Precision@k metric"""
        
        top_k_indices = np.argsort(-predictions)[:k]
        hits = sum([1 for idx in top_k_indices if idx < len(ground_truth) and ground_truth[idx] == 1])
        
        return hits / k if k > 0 else 0


logger.info("ML models module loaded successfully")
