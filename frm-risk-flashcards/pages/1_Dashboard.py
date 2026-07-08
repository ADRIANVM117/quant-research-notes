import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

from src.config import DATABASE_PATH, EXAM_DATE, FRM_STRUCTURE
from src.db import get_all_flashcards


st.title("📊 FRM Study Dashboard")
st.markdown("---")


def load_reviews():
    conn = sqlite3.connect(DATABASE_PATH)

    query = """
    SELECT
        r.id,
        r.flashcard_id,
        r.review_date,
        r.rating,
        f.domain,
        f.chapter,
        f.topic,
        f.difficulty
    FROM reviews r
    LEFT JOIN flashcards f
        ON r.flashcard_id = f.id
    """

    df = pd.read_sql_query(query, conn)
    conn.close()
    df["review_date"] = pd.to_datetime(df["review_date"])
    df["study_day"] = df["review_date"].dt.date

    return df


cards = get_all_flashcards()

cards_columns = [
    "id",
    "domain",
    "chapter",
    "topic",
    "learning_objective",
    "difficulty",
    "question",
    "answer",
    "image_path",
    "created_at"
]

df_cards = pd.DataFrame(cards, columns=cards_columns)

df_reviews = load_reviews()


# Main Metrics
# ==========================================
days_until_exam = (EXAM_DATE - date.today()).days

total_flashcards = len(df_cards)

today = date.today()

today_reviews = df_reviews[df_reviews["study_day"] == today]

cards_reviewed_today = len(today_reviews)

if cards_reviewed_today > 0:
    today_accuracy = (today_reviews["rating"] >= 3).mean()
else:
    today_accuracy = None


col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Days Until Exam",
    days_until_exam
)

col2.metric(
    "Total Flashcards",
    total_flashcards
)

col3.metric(
    "Reviewed Today",
    cards_reviewed_today
)

if today_accuracy is None:
    col4.metric(
        "Today's Accuracy",
        "N/A"
    )
else:
    col4.metric(
        "Today's Accuracy",
        f"{today_accuracy:.1%}"
    )

st.markdown("---")

# Study History
# ==========================================

st.subheader("📈 Study History")

if df_reviews.empty:

    st.info("No study sessions yet.")

else:

    daily_stats = (
        df_reviews
        .assign(correct=df_reviews["rating"] >= 3)
        .groupby("study_day")
        .agg(
            reviewed=("id", "count"),
            accuracy=("correct", "mean")
        )
        .reset_index()
        .sort_values("study_day")
    )

    daily_stats["accuracy"] *= 100
    daily_stats["day"] = (pd.to_datetime(daily_stats["study_day"]).dt.strftime("%d-%b"))

    col_left, col_right = st.columns(2)

    with col_left:

        st.markdown("#### Cards Reviewed")
        st.bar_chart(daily_stats.set_index("day")["reviewed"])
        

    with col_right:

        st.markdown("#### Accuracy (%)")
        st.line_chart(daily_stats.set_index("day")["accuracy"])
        


# ==========================================
# Flashcards by Chapter
# ==========================================

st.subheader("Flashcards by Chapter")

if df_cards.empty:
    st.info("No flashcards added yet.")
else:
    chapter_counts = (
        df_cards
        .groupby("chapter")
        .size()
        .reset_index(name="flashcards")
    )

    st.dataframe(
        chapter_counts,
        use_container_width=True
    )


st.markdown("---")


# ==========================================
# Reviews by Chapter
# ==========================================

st.subheader("Performance by Chapter")

if df_reviews.empty:
    st.info("No reviews yet. Start practicing to generate statistics.")
else:
    chapter_perf = (
        df_reviews
        .assign(correct=df_reviews["rating"] >= 3)
        .groupby("chapter")
        .agg(
            reviews=("id", "count"),
            accuracy=("correct", "mean")
        )
        .reset_index()
    )

    chapter_perf["accuracy"] = chapter_perf["accuracy"].map(
        lambda x: f"{x:.1%}"
    )

    st.dataframe(
        chapter_perf,
        use_container_width=True
    )


st.markdown("---")


# ==========================================
# Topics
# ==========================================

st.subheader("Flashcards by Topic")

if df_cards.empty:
    st.info("No topics available yet.")
else:
    topic_counts = (
        df_cards
        .groupby(["chapter", "topic"])
        .size()
        .reset_index(name="flashcards")
        .sort_values("flashcards", ascending=False)
    )   

    st.dataframe(
        topic_counts,
        use_container_width=True
    )


st.markdown("---")




# ==========================================
# Quick Action
# ==========================================

st.subheader("Next Step")

st.write("Go to **Practice** and review your flashcards.")