"""
ML Model Registry and Management
Manages model versions, deployment, and monitoring
"""

import json
import os
from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class ModelRegistry:
    """Register and track model versions"""
    
    def __init__(self, registry_path: str = '/model_registry'):
        self.registry_path = registry_path
        os.makedirs(registry_path, exist_ok=True)
        self.registry_file = os.path.join(registry_path, 'registry.json')
        self.registry = self._load_registry()
    
    def _load_registry(self) -> Dict:
        """Load existing registry"""
        if os.path.exists(self.registry_file):
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        return {'models': []}
    
    def register_model(self, model_name: str, model_version: str, 
                      metadata: Dict, metrics: Dict) -> str:
        """Register a new model version"""
        
        model_id = f"{model_name}_v{model_version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        model_entry = {
            'id': model_id,
            'name': model_name,
            'version': model_version,
            'created_at': datetime.now().isoformat(),
            'metadata': metadata,
            'metrics': metrics,
            'status': 'staging'
        }
        
        self.registry['models'].append(model_entry)
        self._save_registry()
        
        logger.info(f"Registered model: {model_id}")
        return model_id
    
    def promote_to_production(self, model_id: str) -> bool:
        """Promote model to production"""
        
        for model in self.registry['models']:
            if model['id'] == model_id:
                model['status'] = 'production'
                model['promoted_at'] = datetime.now().isoformat()
                self._save_registry()
                logger.info(f"Promoted {model_id} to production")
                return True
        
        return False
    
    def get_production_model(self, model_name: str) -> Dict:
        """Get current production model"""
        
        for model in self.registry['models']:
            if model['name'] == model_name and model['status'] == 'production':
                return model
        
        return None
    
    def _save_registry(self):
        """Save registry to file"""
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2)


class ModelMonitor:
    """Monitor model performance and data drift"""
    
    def __init__(self):
        self.predictions_log = []
        self.performance_metrics = {}
    
    def log_prediction(self, user_id: int, item_id: int, predicted_rating: float,
                      actual_rating: float = None, model_name: str = 'ensemble'):
        """Log model prediction"""
        
        self.predictions_log.append({
            'user_id': user_id,
            'item_id': item_id,
            'predicted_rating': predicted_rating,
            'actual_rating': actual_rating,
            'model_name': model_name,
            'timestamp': datetime.now().isoformat()
        })
    
    def calculate_metrics(self) -> Dict:
        """Calculate performance metrics"""
        
        if not self.predictions_log:
            return {}
        
        # Filter predictions with actual ratings
        rated_predictions = [p for p in self.predictions_log if p['actual_rating'] is not None]
        
        if not rated_predictions:
            return {}
        
        predictions = [p['predicted_rating'] for p in rated_predictions]
        actuals = [p['actual_rating'] for p in rated_predictions]
        
        # Calculate metrics
        import numpy as np
        mse = np.mean([(p - a) ** 2 for p, a in zip(predictions, actuals)])
        mae = np.mean([abs(p - a) for p, a in zip(predictions, actuals)])
        rmse = np.sqrt(mse)
        
        return {
            'mse': float(mse),
            'mae': float(mae),
            'rmse': float(rmse),
            'total_predictions': len(self.predictions_log),
            'rated_predictions': len(rated_predictions)
        }
    
    def detect_data_drift(self, current_data: Dict, baseline_data: Dict) -> Dict:
        """Detect data drift"""
        
        drift_indicators = {}
        
        for key in current_data:
            if key in baseline_data:
                current_mean = np.mean(current_data[key])
                baseline_mean = np.mean(baseline_data[key])
                
                # Calculate % change
                pct_change = abs((current_mean - baseline_mean) / baseline_mean) * 100
                
                drift_indicators[key] = {
                    'current_mean': float(current_mean),
                    'baseline_mean': float(baseline_mean),
                    'pct_change': float(pct_change),
                    'drifted': pct_change > 10  # 10% threshold
                }
        
        return drift_indicators


# ============================================================================
# ML MODEL KUBERNETES DEPLOYMENT
# ============================================================================

def generate_ml_deployment_manifest() -> str:
    """Generate Kubernetes manifest for ML model serving"""
    
    manifest = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: ml-config
  namespace: recommendation-system
data:
  model_config.json: |
    {
      "models": ["deep_network", "embedding_model", "transformer", "ranking"],
      "ensemble_weights": {
        "deep_network": 0.4,
        "embedding_model": 0.3,
        "ranking": 0.3
      },
      "cache_ttl_hours": 1,
      "max_cache_size": 10000
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-model-server
  namespace: recommendation-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ml-model-server
  template:
    metadata:
      labels:
        app: ml-model-server
    spec:
      containers:
      - name: model-server
        image: ml-model-server:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8001
          name: http
        env:
        - name: MODEL_DIR
          value: /models
        - name: CACHE_SIZE
          value: "10000"
        - name: LOG_LEVEL
          value: INFO
        resources:
          requests:
            cpu: 2000m
            memory: 4Gi
          limits:
            cpu: 4000m
            memory: 8Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8001
          initialDelaySeconds: 20
          periodSeconds: 5
        volumeMounts:
        - name: models
          mountPath: /models
        - name: config
          mountPath: /etc/config
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: ml-models-pvc
      - name: config
        configMap:
          name: ml-config
---
apiVersion: v1
kind: Service
metadata:
  name: ml-model-server
  namespace: recommendation-system
spec:
  selector:
    app: ml-model-server
  ports:
  - name: http
    port: 8001
    targetPort: 8001
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ml-model-server-hpa
  namespace: recommendation-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ml-model-server
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ml-models-pvc
  namespace: recommendation-system
spec:
  accessModes:
    - ReadOnlyMany
  resources:
    requests:
      storage: 50Gi
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: model-retraining
  namespace: recommendation-system
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: training
            image: ml-training:latest
            imagePullPolicy: Always
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: recommendation-secrets
                  key: database-url
            - name: MODEL_DIR
              value: /models
            resources:
              requests:
                cpu: 4000m
                memory: 8Gi
              limits:
                cpu: 8000m
                memory: 16Gi
            volumeMounts:
            - name: models
              mountPath: /models
          volumes:
          - name: models
            persistentVolumeClaim:
              claimName: ml-models-pvc
          restartPolicy: OnFailure
"""
    
    return manifest


# ============================================================================
# ML MODEL MONITORING DASHBOARD
# ============================================================================

def generate_grafana_dashboard() -> Dict:
    """Generate Grafana dashboard for ML model monitoring"""
    
    dashboard = {
        "dashboard": {
            "title": "ML Model Monitoring",
            "panels": [
                {
                    "title": "Model Prediction Latency",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(ml_inference_duration_seconds_bucket[5m]))"
                        }
                    ]
                },
                {
                    "title": "Model Accuracy (MAE)",
                    "targets": [
                        {
                            "expr": "ml_model_mae{model='ensemble'}"
                        }
                    ]
                },
                {
                    "title": "Data Drift Detection",
                    "targets": [
                        {
                            "expr": "ml_data_drift_indicator"
                        }
                    ]
                },
                {
                    "title": "Cache Hit Rate",
                    "targets": [
                        {
                            "expr": "rate(ml_cache_hits_total[5m]) / rate(ml_cache_requests_total[5m])"
                        }
                    ]
                },
                {
                    "title": "Model Inference QPS",
                    "targets": [
                        {
                            "expr": "rate(ml_predictions_total[1m])"
                        }
                    ]
                }
            ]
        }
    }
    
    return dashboard
