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
    "created_at"
]

df_cards = pd.DataFrame(cards, columns=cards_columns)

df_reviews = load_reviews()


# ==========================================
# Main Metrics
# ==========================================

days_until_exam = (EXAM_DATE - date.today()).days

total_flashcards = len(df_cards)

total_reviews = len(df_reviews)

if total_reviews > 0:
    accuracy = (df_reviews["rating"] >= 3).mean()
else:
    accuracy = None


col1, col2, col3, col4 = st.columns(4)

col1.metric("Days Until Exam", days_until_exam)

col2.metric("Total Flashcards", total_flashcards)

col3.metric("Cards Reviewed", total_reviews)

if accuracy is None:
    col4.metric("Accuracy", "N/A")
else:
    col4.metric("Accuracy", f"{accuracy:.1%}")


st.markdown("---")


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