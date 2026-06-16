"""
ML Model Serving FastAPI Application
Loads trained models and provides real-time inference API
"""

import os
import json
import logging
import numpy as np
import joblib
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import tensorflow as tf
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# FastAPI App
app = FastAPI(title="ML Model Serving", version="1.0.0")

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class PredictionRequest(BaseModel):
    user_id: int
    item_id: int
    user_features: List[float]
    item_features: List[float]
    method: str = "ensemble"

class RecommendationRequest(BaseModel):
    user_id: int
    num_recommendations: int = 10
    user_features: List[float]
    candidate_items: List[int]
    items_features: List[List[float]]

class RecommendationResponse(BaseModel):
    item_id: int
    score: float
    method: str

# ============================================================================
# MODEL LOADING
# ============================================================================

class ModelServer:
    """Load and serve trained models for inference"""
    
    def __init__(self, model_dir: str = '/models'):
        self.model_dir = model_dir
        self.models = {}
        self.metadata = {}
        self.feature_engineer = None
        self.scaler = None
        
    def load_latest_models(self):
        """Load latest trained models"""
        
        logger.info(f"Loading models from {self.model_dir}")
        
        # Find latest metadata
        if not os.path.exists(self.model_dir):
            logger.warning(f"Model directory {self.model_dir} not found")
            return False
        
        metadata_files = [f for f in os.listdir(self.model_dir) if f.startswith('metadata_')]
        if not metadata_files:
            logger.warning("No metadata files found")
            return False
        
        latest_metadata = sorted(metadata_files)[-1]
        metadata_path = os.path.join(self.model_dir, latest_metadata)
        
        try:
            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)
            logger.info(f"Loaded metadata: {latest_metadata}")
        except Exception as e:
            logger.error(f"Error loading metadata: {e}")
            return False
        
        timestamp = self.metadata.get('timestamp', '')
        
        # Load each model
        for model_name in self.metadata.get('models', []):
            model_path = os.path.join(self.model_dir, f'{model_name}_{timestamp}.pkl')
            
            if os.path.exists(model_path):
                try:
                    self.models[model_name] = joblib.load(model_path)
                    logger.info(f"Loaded {model_name}")
                except Exception as e:
                    logger.error(f"Error loading {model_name}: {e}")
            else:
                h5_path = model_path.replace('.pkl', '.h5')
                if os.path.exists(h5_path):
                    try:
                        self.models[model_name] = tf.keras.models.load_model(h5_path)
                        logger.info(f"Loaded {model_name} (TensorFlow)")
                    except Exception as e:
                        logger.error(f"Error loading {model_name}: {e}")
        
        logger.info(f"Loaded {len(self.models)} models")
        return len(self.models) > 0
    
    def predict_rating(self, user_id: int, item_id: int, 
                      user_features: np.ndarray, item_features: np.ndarray,
                      method: str = 'ensemble') -> float:
        """Predict rating for user-item pair"""
        
        try:
            if method == 'ensemble' and 'ensemble' in self.models:
                pred = self.models['ensemble'].predict(
                    user_features.reshape(1, -1),
                    item_features.reshape(1, -1)
                )
                return float(pred[0][0] * 5.0)
            
            elif method == 'deep_network' and 'deep_network' in self.models:
                pred = self.models['deep_network'].predict(
                    user_features.reshape(1, -1),
                    item_features.reshape(1, -1)
                )
                return float(pred[0][0] * 5.0)
            
            else:
                logger.warning(f"Model {method} not found")
                return 3.0
        
        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            return 3.0
    
    def rank_items(self, user_id: int, candidate_items: List[int],
                   user_features: np.ndarray, items_features: List[np.ndarray]) -> List[Tuple[int, float]]:
        """Rank candidate items"""
        
        try:
            if 'ranking' not in self.models:
                logger.warning("Ranking model not found")
                return [(item_id, 1.0) for item_id in candidate_items]
            
            ranking_model = self.models['ranking']
            
            X_rank = []
            for item_id, item_feat in zip(candidate_items, items_features):
                combined_feat = np.concatenate([user_features, item_feat])
                X_rank.append(combined_feat)
            
            X_rank = np.array(X_rank)
            scores = ranking_model.predict(X_rank)
            
            ranked = sorted(zip(candidate_items, scores), key=lambda x: x[1], reverse=True)
            return ranked
        
        except Exception as e:
            logger.error(f"Error ranking items: {e}")
            return [(item_id, 1.0) for item_id in candidate_items]


# Initialize model server
model_server = ModelServer()

# ============================================================================
# FASTAPI ENDPOINTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Load models on startup"""
    logger.info("Starting ML Model Server...")
    success = model_server.load_latest_models()
    if not success:
        logger.warning("No models loaded - running in demo mode")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "models_loaded": len(model_server.models)
    }

@app.get("/ready")
async def ready_check():
    """Readiness check"""
    if len(model_server.models) > 0:
        return {"status": "ready"}
    else:
        raise HTTPException(status_code=503, detail="Models not loaded")

@app.post("/predict")
async def predict(request: PredictionRequest) -> Dict:
    """Predict rating for user-item pair"""
    
    try:
        user_features = np.array(request.user_features)
        item_features = np.array(request.item_features)
        
        prediction = model_server.predict_rating(
            request.user_id,
            request.item_id,
            user_features,
            item_features,
            method=request.method
        )
        
        return {
            "user_id": request.user_id,
            "item_id": request.item_id,
            "predicted_rating": prediction,
            "method": request.method,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in /predict: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recommendations")
async def get_recommendations(request: RecommendationRequest) -> List[RecommendationResponse]:
    """Get recommendations for user"""
    
    try:
        user_features = np.array(request.user_features)
        items_features = [np.array(f) for f in request.items_features]
        
        ranked = model_server.rank_items(
            request.user_id,
            request.candidate_items,
            user_features,
            items_features
        )
        
        recommendations = []
        for item_id, score in ranked[:request.num_recommendations]:
            recommendations.append(RecommendationResponse(
                item_id=int(item_id),
                score=float(score),
                method="ranking"
            ))
        
        return recommendations
    
    except Exception as e:
        logger.error(f"Error in /recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def list_models() -> Dict:
    """List loaded models"""
    return {
        "loaded_models": list(model_server.models.keys()),
        "metadata": model_server.metadata,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/metrics")
async def get_metrics() -> Dict:
    """Get model server metrics"""
    return {
        "models_loaded": len(model_server.models),
        "model_names": list(model_server.models.keys()),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, workers=4)
