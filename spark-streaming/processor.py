"""
Apache Spark Streaming: Real-time processing of events
Processes Kafka events and updates user profiles, content popularity, etc.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, window, count, avg, max, min
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, LongType
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_spark_session():
    """Create Spark session with Kafka integration"""
    return SparkSession.builder \
        .appName("RecommendationEngineStreaming") \
        .config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoints") \
        .getOrCreate()

def define_schemas():
    """Define event schemas"""
    watch_schema = StructType([
        StructField("user_id", IntegerType()),
        StructField("content_id", IntegerType()),
        StructField("duration", IntegerType()),
        StructField("watch_time", IntegerType()),
        StructField("timestamp", StringType()),
        StructField("event_type", StringType())
    ])
    
    like_schema = StructType([
        StructField("user_id", IntegerType()),
        StructField("content_id", IntegerType()),
        StructField("liked", StringType()),
        StructField("timestamp", StringType()),
        StructField("event_type", StringType())
    ])
    
    rating_schema = StructType([
        StructField("user_id", IntegerType()),
        StructField("content_id", IntegerType()),
        StructField("rating", DoubleType()),
        StructField("timestamp", StringType()),
        StructField("event_type", StringType())
    ])
    
    return {
        'watch': watch_schema,
        'like': like_schema,
        'rating': rating_schema
    }

def process_watch_events(spark):
    """Process watch events in real-time"""
    kafka_brokers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    schemas = define_schemas()
    
    # Read from Kafka
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_brokers) \
        .option("subscribe", "watch-events") \
        .option("startingOffsets", "earliest") \
        .load()
    
    # Parse JSON
    watch_df = df.select(
        from_json(col("value").cast("string"), schemas['watch']).alias("data")
    ).select("data.*")
    
    # Add processing timestamp
    watch_df = watch_df.withColumn(
        "processing_time",
        col("timestamp").cast("timestamp")
    )
    
    # Windowed aggregations (1-minute windows)
    popular_content = watch_df \
        .groupBy(
            window(col("processing_time"), "1 minute"),
            col("content_id")
        ) \
        .agg(
            count("*").alias("watch_count"),
            avg("watch_time").alias("avg_watch_time")
        ) \
        .filter(col("watch_count") > 10)
    
    # Write to console (for monitoring)
    query1 = popular_content \
        .writeStream \
        .format("console") \
        .option("truncate", "false") \
        .option("checkpointLocation", "/tmp/checkpoints/watch-popular") \
        .start()
    
    # User watch patterns
    user_watches = watch_df \
        .groupBy(col("user_id")) \
        .agg(count("*").alias("total_watches"))
    
    query2 = user_watches \
        .writeStream \
        .format("console") \
        .option("checkpointLocation", "/tmp/checkpoints/user-watches") \
        .start()
    
    return query1, query2

def process_rating_events(spark):
    """Process rating events"""
    kafka_brokers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    schemas = define_schemas()
    
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_brokers) \
        .option("subscribe", "rating-events") \
        .option("startingOffsets", "earliest") \
        .load()
    
    rating_df = df.select(
        from_json(col("value").cast("string"), schemas['rating']).alias("data")
    ).select("data.*")
    
    # Real-time content ratings
    content_ratings = rating_df \
        .groupBy(col("content_id")) \
        .agg(
            avg("rating").alias("avg_rating"),
            count("*").alias("rating_count"),
            min("rating").alias("min_rating"),
            max("rating").alias("max_rating")
        )
    
    query = content_ratings \
        .writeStream \
        .format("console") \
        .option("checkpointLocation", "/tmp/checkpoints/content-ratings") \
        .start()
    
    return query

def process_like_events(spark):
    """Process like/unlike events"""
    kafka_brokers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    schemas = define_schemas()
    
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_brokers) \
        .option("subscribe", "like-events") \
        .option("startingOffsets", "earliest") \
        .load()
    
    like_df = df.select(
        from_json(col("value").cast("string"), schemas['like']).alias("data")
    ).select("data.*")
    
    # Like statistics
    like_stats = like_df \
        .groupBy(col("content_id")) \
        .agg(
            count(col("liked")).alias("like_count"),
            (count(col("liked")) * 100.0 / count("*")).alias("like_percentage")
        )
    
    query = like_stats \
        .writeStream \
        .format("console") \
        .option("checkpointLocation", "/tmp/checkpoints/like-stats") \
        .start()
    
    return query

def main():
    logger.info("Starting Spark Streaming for Recommendation Engine")
    
    spark = create_spark_session()
    
    # Process all event types
    watch_queries = process_watch_events(spark)
    rating_query = process_rating_events(spark)
    like_query = process_like_events(spark)
    
    logger.info("Streaming queries started")
    
    # Await termination
    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    main()
