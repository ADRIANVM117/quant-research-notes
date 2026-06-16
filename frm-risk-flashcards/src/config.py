from pathlib import Path
from datetime import date

# Root directory
ROOT_DIR = Path(__file__).resolve().parent.parent

# Database
DATABASE_PATH = ROOT_DIR / "database" / "frm_flashcards.db"

# FRM Chapters
CHAPTERS = [
    "Foundations of Risk Management",
    "Quantitative Analysis",
    "Financial Markets and Products",
    "Valuation and Risk Models"
]

# Exam Date
EXAM_DATE = date(2026, 8, 9)