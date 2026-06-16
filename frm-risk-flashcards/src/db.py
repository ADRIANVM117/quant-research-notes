import sqlite3

from src.config import DATABASE_PATH

def create_database():

    conn = sqlite3.connect(DATABASE_PATH)

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS flashcards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chapter TEXT NOT NULL,
        topic TEXT NOT NULL,
        difficulty TEXT NOT NULL,
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


if __name__ == "__main__":
    create_database()
    print("Database created successfully.")