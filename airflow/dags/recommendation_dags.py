"""
Airflow DAGs for batch processing and model retraining
Orchestrates data pipelines, model training, and scheduled recommendations
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Default arguments
default_args = {
    'owner': 'recommendation-engine',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# DAG 1: Daily model retraining
dag_retrain = DAG(
    'recommendation_model_retraining',
    default_args=default_args,
    description='Retrain recommendation models daily',
    schedule_interval='0 2 * * *',  # 2 AM daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['recommendation', 'ml', 'daily']
)

def extract_interactions():
    """Extract recent user interactions"""
    import pandas as pd
    from sqlalchemy import create_engine
    import os
    
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url)
    
    query = """
    SELECT user_id, content_id, rating, interaction_type, timestamp
    FROM user_interactions
    WHERE timestamp >= NOW() - INTERVAL '30 days'
    ORDER BY timestamp DESC
    """
    
    df = pd.read_sql(query, engine)
    df.to_parquet('/tmp/interactions.parquet', index=False)
    logger.info(f"Extracted {len(df)} interactions")
    
    return len(df)

def extract_content():
    """Extract content metadata"""
    import pandas as pd
    from sqlalchemy import create_engine
    import os
    
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url)
    
    query = "SELECT * FROM content"
    df = pd.read_sql(query, engine)
    df.to_parquet('/tmp/content.parquet', index=False)
    logger.info(f"Extracted {len(df)} content items")
    
    return len(df)

def train_models():
    """Train recommendation models"""
    import pandas as pd
    from recommendation_engine.recommender import HybridRecommender
    import pickle
    
    # Load data
    interactions_df = pd.read_parquet('/tmp/interactions.parquet')
    content_df = pd.read_parquet('/tmp/content.parquet')
    
    # Train model
    model = HybridRecommender()
    model.fit(interactions_df, content_df)
    
    # Save model
    with open('/tmp/hybrid_model.pkl', 'wb') as f:
        pickle.dump(model, f)
    
    logger.info("Models trained and saved")

def generate_recommendations():
    """Generate recommendations for all active users"""
    import pandas as pd
    import pickle
    from sqlalchemy import create_engine
    import os
    
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url)
    
    # Load model
    with open('/tmp/hybrid_model.pkl', 'rb') as f:
        model = pickle.load(f)
    
    # Get active users
    users = pd.read_sql(
        "SELECT DISTINCT user_id FROM user_interactions WHERE timestamp >= NOW() - INTERVAL '7 days'",
        engine
    )
    
    recommendations = []
    for user_id in users['user_id']:
        # Get user history
        history = pd.read_sql(
            f"SELECT content_id FROM user_interactions WHERE user_id = {user_id} ORDER BY timestamp DESC LIMIT 50",
            engine
        )
        
        user_history = history['content_id'].tolist()
        
        # Get recommendations
        recs = model.get_recommendations(user_id, user_history, n_items=5000, n_recommendations=10)
        
        for content_id, score in recs:
            recommendations.append({
                'user_id': user_id,
                'content_id': content_id,
                'score': score,
                'generated_at': datetime.utcnow()
            })
    
    # Save recommendations
    if recommendations:
        recs_df = pd.DataFrame(recommendations)
        
        # Insert into database
        recs_df.to_sql('recommendations', engine, if_exists='append', index=False)
        logger.info(f"Generated {len(recommendations)} recommendations")

# Tasks for DAG 1
extract_interactions_task = PythonOperator(
    task_id='extract_interactions',
    python_callable=extract_interactions,
    dag=dag_retrain
)

extract_content_task = PythonOperator(
    task_id='extract_content',
    python_callable=extract_content,
    dag=dag_retrain
)

train_models_task = PythonOperator(
    task_id='train_models',
    python_callable=train_models,
    dag=dag_retrain
)

generate_recs_task = PythonOperator(
    task_id='generate_recommendations',
    python_callable=generate_recommendations,
    dag=dag_retrain
)

# DAG dependencies
[extract_interactions_task, extract_content_task] >> train_models_task >> generate_recs_task

# DAG 2: Data quality checks
dag_quality = DAG(
    'data_quality_checks',
    default_args=default_args,
    description='Run data quality checks',
    schedule_interval='0 3 * * *',  # 3 AM daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['quality', 'daily']
)

check_null_interactions = PostgresOperator(
    task_id='check_null_interactions',
    postgres_conn_id='postgres_default',
    sql="""
    SELECT COUNT(*) FROM user_interactions
    WHERE user_id IS NULL OR content_id IS NULL
    """,
    dag=dag_quality
)

check_duplicate_interactions = PostgresOperator(
    task_id='check_duplicate_interactions',
    postgres_conn_id='postgres_default',
    sql="""
    SELECT user_id, content_id, COUNT(*) as count
    FROM user_interactions
    GROUP BY user_id, content_id
    HAVING COUNT(*) > 1
    """,
    dag=dag_quality
)

# DAG 3: Backup and archival
dag_backup = DAG(
    'data_backup',
    default_args=default_args,
    description='Backup recommendation data',
    schedule_interval='0 1 * * *',  # 1 AM daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['backup', 'daily']
)

backup_task = BashOperator(
    task_id='backup_database',
    bash_command='pg_dump $DATABASE_URL > /backups/recommendations_$(date +%Y%m%d).sql',
    dag=dag_backup
)
