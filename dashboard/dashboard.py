import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from datetime import datetime

# ==========================================
# PAGE CONFIG
# ==========================================

st.set_page_config(
    page_title="AI Recommendation Dashboard",
    page_icon="🎬",
    layout="wide"
)

# ==========================================
# DATABASE CONNECTION
# ==========================================

DATABASE_URL = (
    "postgresql+psycopg2://admin:admin@postgres:5432/movies_db"
)

engine = create_engine(DATABASE_URL)

# ==========================================
# AUTO REFRESH
# ==========================================

st.markdown(
    """
    <meta http-equiv="refresh" content="10">
    """,
    unsafe_allow_html=True
)

# ==========================================
# TITLE
# ==========================================

st.title("🎬 Real-Time AI Recommendation Dashboard")

st.markdown("---")

# ==========================================
# LOAD DATA
# ==========================================

try:

    query = """
    SELECT *
    FROM movie_events
    ORDER BY event_time DESC
    """

    df = pd.read_sql(query, engine)

except Exception as e:

    st.error(f"Database Error: {e}")
    st.stop()

# ==========================================
# CHECK DATA
# ==========================================

if df.empty:

    st.warning("No streaming data available")
    st.stop()

# ==========================================
# METRICS
# ==========================================

total_users = df["user_id"].nunique()

total_movies = df["movie_id"].nunique()

avg_rating = round(df["rating"].mean(), 2)

total_watch_time = int(df["watch_time"].sum())

# ==========================================
# TOP METRICS
# ==========================================

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "👥 Active Users",
    total_users
)

col2.metric(
    "🎥 Movies",
    total_movies
)

col3.metric(
    "⭐ Avg Rating",
    avg_rating
)

col4.metric(
    "⏱ Total Watch Time",
    total_watch_time
)

st.markdown("---")

# ==========================================
# TRENDING MOVIES
# ==========================================

st.subheader("🔥 Trending Movies")

movie_stats = df.groupby(
    "movie_name"
).agg({
    "movie_id": "count",
    "rating": "mean",
    "watch_time": "sum"
}).reset_index()

movie_stats.columns = [
    "movie_name",
    "views",
    "avg_rating",
    "watch_time"
]

movie_stats = movie_stats.sort_values(
    by="views",
    ascending=False
)

fig_movies = px.bar(
    movie_stats,
    x="movie_name",
    y="views",
    hover_data=["avg_rating", "watch_time"],
    title="Most Watched Movies"
)

st.plotly_chart(
    fig_movies,
    use_container_width=True
)

# ==========================================
# GENRE DISTRIBUTION
# ==========================================

st.subheader("🎭 Genre Distribution")

genre_stats = df.groupby(
    "genre"
).size().reset_index(name="count")

fig_genre = px.pie(
    genre_stats,
    names="genre",
    values="count",
    title="Genre Popularity"
)

st.plotly_chart(
    fig_genre,
    use_container_width=True
)

# ==========================================
# USER WATCH TIME
# ==========================================

st.subheader("👤 User Watch Analytics")

user_stats = df.groupby(
    "user_id"
).agg({
    "watch_time": "sum",
    "rating": "mean"
}).reset_index()

user_stats.columns = [
    "user_id",
    "total_watch_time",
    "avg_rating"
]

fig_users = px.bar(
    user_stats,
    x="user_id",
    y="total_watch_time",
    color="avg_rating",
    title="User Engagement"
)

st.plotly_chart(
    fig_users,
    use_container_width=True
)

# ==========================================
# EVENT TYPE ANALYTICS
# ==========================================

st.subheader("📊 Event Type Analytics")

event_stats = df.groupby(
    "event_type"
).size().reset_index(name="count")

fig_events = px.bar(
    event_stats,
    x="event_type",
    y="count",
    title="Event Distribution"
)

st.plotly_chart(
    fig_events,
    use_container_width=True
)

# ==========================================
# RECENT STREAMING EVENTS
# ==========================================

st.subheader("📡 Live Streaming Events")

latest_events = df.sort_values(
    by="event_time",
    ascending=False
).head(20)

st.dataframe(
    latest_events,
    use_container_width=True
)

# ==========================================
# FOOTER
# ==========================================

st.markdown("---")

st.caption(
    f"Last Updated: {datetime.now()}"
)
