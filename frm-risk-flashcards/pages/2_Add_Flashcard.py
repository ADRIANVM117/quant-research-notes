import streamlit as st
from pathlib import Path
import shutil
from datetime import datetime
from src.config import (
    DOMAINS,
    FRM_STRUCTURE
)

from src.db import add_flashcard


st.title("➕ Add Flashcard")

st.markdown("---")

# ==========================================
# Domain
# ==========================================

domain = st.selectbox(
    "Domain",
    DOMAINS
)

# ==========================================
# Chapter
# ==========================================

chapter = st.selectbox(
    "Chapter",
    list(FRM_STRUCTURE.keys())
)

# ==========================================
# Topic (depends on Chapter)
# ==========================================

topic = st.selectbox(
    "Topic",
    FRM_STRUCTURE[chapter]
)

# ==========================================
# Difficulty
# ==========================================

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

# ==========================================
# LaTeX Help
# ==========================================

st.info("""
**Markdown + LaTeX Supported**

Inline formula:

`$E(X)$`

Block formula:

$$
P(A|B)=\\frac{P(B|A)P(A)}{P(B)}
$$
""")

question = st.text_area(
    "Question",
    height=180,
    placeholder="""Example:

What is Bayes' Theorem?

$$
P(A|B)=?
$$
"""
)

answer = st.text_area(
    "Answer",
    height=180,
    placeholder="""Example:

Bayes' Theorem:

$$
P(A|B)=
\\frac{P(B|A)P(A)}
{P(B)}
$$
"""
)

# ==========================================
# Optional Image
# ==========================================

uploaded_image = st.file_uploader(
    "📎 Upload image (optional)",
    type=["png", "jpg", "jpeg"]
)
st.caption(
    "Images are optional. Use them for diagrams, distributions, tables or figures."
)

if uploaded_image is not None:
    st.image(
        uploaded_image,
        caption="Question Image",
        use_container_width=True
    )


st.markdown("---")
st.subheader(" Preview")

if question.strip():
    st.markdown("### ❓ Question")
    st.markdown(question)
    if uploaded_image is not None:
        st.image(
            uploaded_image,
            use_container_width=True
        )

else:
    st.info("Question preview will appear here.")

if answer.strip():
    st.markdown("### ✅ Answer")
    st.markdown(answer)
else:
    st.info("Answer preview will appear here.") #---------------------

if st.button("💾 Save Flashcard", use_container_width=True):
    if not question.strip():
        st.error("Question is required.")

    elif not answer.strip():
        st.error("Answer is required.")

    else:
        add_flashcard(
        domain=domain,
        chapter=chapter,
        topic=topic,
        learning_objective="",
        difficulty=difficulty,
        question=question,
        answer=answer)
        st.success("Flashcard saved successfully.")