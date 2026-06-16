from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup

# ==========================================
# DEFAULT ARGUMENTS
# ==========================================

default_args = {

    "owner": "sujoy",

    "depends_on_past": False,

    "email_on_failure": False,

    "email_on_retry": False,

    "retries": 3,

    "retry_delay": timedelta(minutes=5),

    "execution_timeout": timedelta(minutes=30)

}

# ==========================================
# DAG
# ==========================================

with DAG(

    dag_id="movie_recommendation_retraining",

    description="Production ALS Model Retraining Pipeline",

    default_args=default_args,

    start_date=datetime(2026, 1, 1),

    schedule="@hourly",

    catchup=False,

    max_active_runs=1,

    tags=[
        "ml",
        "spark",
        "recommendation",
        "production"
    ]

) as dag:

    # ==========================================
    # START TASK
    # ==========================================

    start_pipeline = BashOperator(

        task_id="start_pipeline",

        bash_command="""
        echo '🚀 Starting Recommendation Training Pipeline'
        """

    )

    # ==========================================
    # TRAINING GROUP
    # ==========================================

    with TaskGroup(

        group_id="training_pipeline"

    ) as training_pipeline:

        # ======================================
        # TRAIN MODEL
        # ======================================

        train_model = BashOperator(

            task_id="train_als_model",

            bash_command="""
            set -e

            echo '🚀 Starting ALS Training'

            spark-submit /opt/airflow/train_model.py

            echo '✅ ALS Training Completed'
            """,

            retries=3,

            retry_delay=timedelta(minutes=2)

        )

        # ======================================
        # VALIDATE MODEL
        # ======================================

        validate_model = BashOperator(

    task_id="validate_model",

    bash_command="""

    echo '🔍 Validating Trained Model'

    MODEL_PATH="/opt/airflow/models/movie_recommendation_model"

    # ==========================================
    # CHECK MODEL DIRECTORY
    # ==========================================

    if [ ! -d "$MODEL_PATH" ]; then

        echo '❌ Model Directory Not Found'

        exit 1

    fi

    # ==========================================
    # CHECK MODEL FILES
    # ==========================================

    if [ -z "$(ls -A $MODEL_PATH)" ]; then

        echo '❌ Model Directory Empty'

        exit 1

    fi

    # ==========================================
    # SUCCESS
    # ==========================================

    echo '✅ Model Validation Successful'

    echo "📦 Model Path: $MODEL_PATH"

    """

)

        # ======================================
        # PIPELINE ORDER
        # ======================================

        train_model >> validate_model

    # ==========================================
    # CLEANUP TASK
    # ==========================================

    cleanup = BashOperator(

        task_id="cleanup_temp_files",

        bash_command="""
        echo '🧹 Cleaning Temporary Files'

        rm -rf /tmp/spark-events/* || true

        echo '✅ Cleanup Completed'
        """

    )

    # ==========================================
    # END TASK
    # ==========================================

    finish_pipeline = BashOperator(

        task_id="finish_pipeline",

        bash_command="""
        echo '🎉 Recommendation Pipeline Finished Successfully'
        """

    )

    # ==========================================
    # DAG FLOW
    # ==========================================

    start_pipeline >> training_pipeline >> cleanup >> finish_pipeline