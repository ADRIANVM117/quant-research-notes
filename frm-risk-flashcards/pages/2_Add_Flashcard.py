import streamlit as st

from src.config import (
    DOMAINS,
    FRM_PART_1_CHAPTERS
)

from src.db import add_flashcard


st.title("➕ Add Flashcard")

st.markdown("---")


domain = st.selectbox(
    "Domain",
    DOMAINS
)


chapter = st.selectbox(
    "Chapter",
    FRM_PART_1_CHAPTERS
)


topic = st.text_input(
    "Topic"
)


learning_objective = st.text_input(
    "Learning Objective"
)


difficulty_label = st.selectbox(
    "Difficulty",
    [
        "Easy",
        "Medium",
        "Hard"
    ]
)


difficulty_mapping = {
    "Easy": 1,
    "Medium": 2,
    "Hard": 3
}

difficulty = difficulty_mapping[difficulty_label]


question = st.text_area(
    "Question",
    height=120
)


answer = st.text_area(
    "Answer",
    height=120
)


if st.button("Save Flashcard"):

    if not topic:
        st.error("Topic is required.")

    elif not question:
        st.error("Question is required.")

    elif not answer:
        st.error("Answer is required.")

    else:

        add_flashcard(
            domain=domain,
            chapter=chapter,
            topic=topic,
            learning_objective=learning_objective,
            difficulty=difficulty,
            question=question,
            answer=answer
        )

        st.success(
            "Flashcard saved successfully."
        )