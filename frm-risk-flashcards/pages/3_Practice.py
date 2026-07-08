import streamlit as st

from src.config import DOMAINS, FRM_STRUCTURE
from src.db import get_random_flashcard, add_review


st.title("🧠 Practice")
st.markdown("---")


if "current_flashcard" not in st.session_state:
    st.session_state.current_flashcard = None

if "show_answer" not in st.session_state:
    st.session_state.show_answer = False


domain = st.selectbox("Domain", DOMAINS)

chapter = st.selectbox(
    "Chapter",
    ["All Chapters"] + list(FRM_STRUCTURE.keys())
)

if chapter == "All Chapters":
    topic = "All Topics"
    selected_chapter = None
    selected_topic = None
else:
    topic = st.selectbox(
        "Topic",
        ["All Topics"] + FRM_STRUCTURE[chapter]
    )
    selected_chapter = chapter
    selected_topic = None if topic == "All Topics" else topic


def load_next_card():
    st.session_state.current_flashcard = get_random_flashcard(
        domain=domain,
        chapter=selected_chapter,
        topic=selected_topic
    )
    st.session_state.show_answer = False


if st.button("🎲 Get Flashcard", use_container_width=True):
    load_next_card()


card = st.session_state.current_flashcard

if card:

    (
        flashcard_id,
        card_domain,
        card_chapter,
        card_topic,
        learning_objective,
        difficulty,
        question,
        answer,
        image_path,
        created_at
    ) = card

    st.markdown("---")

    st.caption(f"Chapter: {card_chapter}")
    st.caption(f"Topic: {card_topic}")
    difficulty_label = {1: "🟢 Easy",2: "🟠 Medium",3: "🔴 Hard"}
    st.caption(f"Difficulty: {difficulty_label[difficulty]}")

    st.markdown("## ❓ Question")
    with st.container(border=True):
        if image_path:
            col_question, col_image = st.columns([3, 2])

            with col_question:
                st.markdown(question)

            with col_image:
                st.image(
                image_path,
                use_container_width=True,
                output_format="PNG"
                )
        else:
            st.markdown(question)
    st.write("")

    if not st.session_state.show_answer:

        if st.button("Show Answer", use_container_width=True):
            st.session_state.show_answer = True
            st.rerun()

    else:

        st.markdown("## ✅ Answer")
        with st.container(border=True):
            st.markdown(answer)
        st.write("")


        st.markdown("---")

        col1, col2, col3, col4 = st.columns(4)

        if col1.button("🔴 Again", use_container_width=True):
            add_review(flashcard_id, 1)
            load_next_card()
            st.rerun()

        if col2.button("🟠 Hard", use_container_width=True):
            add_review(flashcard_id, 2)
            load_next_card()
            st.rerun()

        if col3.button("🟢 Good", use_container_width=True):
            add_review(flashcard_id, 3)
            load_next_card()
            st.rerun()

        if col4.button("🔵 Easy", use_container_width=True):
            add_review(flashcard_id, 4)
            load_next_card()
            st.rerun()

else:
    st.info("Select a chapter/topic and click Get Flashcard.")