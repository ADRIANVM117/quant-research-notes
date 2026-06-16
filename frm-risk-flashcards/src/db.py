import sqlite3

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
    INSERT INTO flashcards (
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


def delete_flashcard(flashcard_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM flashcards
    WHERE id = ?
    """, (flashcard_id,))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_database()
    print("Database created successfully.")