import sqlite3
import random

from src.config import DATABASE_PATH


def get_connection():
    return sqlite3.connect(DATABASE_PATH)


def create_database():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS flashcards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        domain TEXT NOT NULL,
        chapter TEXT NOT NULL,
        topic TEXT NOT NULL,
        learning_objective TEXT,

        difficulty INTEGER NOT NULL,

        question TEXT NOT NULL,
        answer TEXT NOT NULL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        flashcard_id INTEGER NOT NULL,

        review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        rating INTEGER NOT NULL,

        FOREIGN KEY (flashcard_id)
        REFERENCES flashcards(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS study_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        session_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        cards_reviewed INTEGER,
        accuracy REAL,
        duration_minutes REAL
    )
    """)

    conn.commit()
    conn.close()


# -----------------------------------------------------
# FLASHCARDS
# -----------------------------------------------------

def add_flashcard(
    domain,
    chapter,
    topic,
    learning_objective,
    difficulty,
    question,
    answer
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO flashcards(
        domain,
        chapter,
        topic,
        learning_objective,
        difficulty,
        question,
        answer
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        domain,
        chapter,
        topic,
        learning_objective,
        difficulty,
        question,
        answer
    ))

    conn.commit()
    conn.close()


def get_all_flashcards():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        domain,
        chapter,
        topic,
        learning_objective,
        difficulty,
        question,
        answer,
        created_at
    FROM flashcards
    ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


def get_flashcards_by_filters(
    domain=None,
    chapter=None,
    topic=None
):

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT *
    FROM flashcards
    WHERE 1=1
    """

    params = []

    if domain:
        query += " AND domain = ?"
        params.append(domain)

    if chapter:
        query += " AND chapter = ?"
        params.append(chapter)

    if topic:
        query += " AND topic = ?"
        params.append(topic)

    cursor.execute(query, params)

    cards = cursor.fetchall()

    conn.close()

    return cards


def get_random_flashcard(
    domain=None,
    chapter=None,
    topic=None
):

    cards = get_flashcards_by_filters(
        domain,
        chapter,
        topic
    )

    if not cards:
        return None

    return random.choice(cards)


def delete_flashcard(flashcard_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM flashcards
    WHERE id = ?
    """, (flashcard_id,))

    conn.commit()
    conn.close()


# -----------------------------------------------------
# REVIEWS
# -----------------------------------------------------

def add_review(
    flashcard_id,
    rating
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO reviews(
        flashcard_id,
        rating
    )
    VALUES (?, ?)
    """, (
        flashcard_id,
        rating
    ))

    conn.commit()
    conn.close()


# -----------------------------------------------------
# TEST
# -----------------------------------------------------

if __name__ == "__main__":

    create_database()

    print("Database created successfully.")