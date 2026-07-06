import streamlit as st
import pandas as pd

from src.db import get_all_flashcards, delete_flashcard


st.title("📋 View Flashcards")

cards = get_all_flashcards()

columns = [
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

df = pd.DataFrame(cards, columns=columns)

if df.empty:
    st.info("No flashcards saved yet.")
else:
    st.metric("Total Flashcards", len(df))

    chapter_filter = st.selectbox(
        "Filter by Chapter",
        ["All"] + sorted(df["chapter"].unique().tolist())
    )

    if chapter_filter != "All":
        df = df[df["chapter"] == chapter_filter]

    topic_filter = st.selectbox(
        "Filter by Topic",
        ["All"] + sorted(df["topic"].unique().tolist())
    )

    if topic_filter != "All":
        df = df[df["topic"] == topic_filter]

    st.dataframe(
        df[
            [
                "id",
                "domain",
                "chapter",
                "topic",
                "learning_objective",
                "difficulty",
                "question",
                "answer"
            ]
        ],
        use_container_width=True
    )

    st.markdown("---")

    st.subheader("Delete Flashcard")

    flashcard_id = st.number_input(
        "Flashcard ID",
        min_value=1,
        step=1
    )

    if st.button("Delete Flashcard"):
        delete_flashcard(int(flashcard_id))
        st.success(f"Flashcard {flashcard_id} deleted.")
        st.rerun()