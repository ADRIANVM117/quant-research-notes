from pathlib import Path
from datetime import date

# ==========================================
# PATHS
# ==========================================

ROOT_DIR = Path(__file__).resolve().parent.parent

DATABASE_PATH = ROOT_DIR / "database" / "frm_flashcards.db"


# ==========================================
# EXAM
# ==========================================

EXAM_DATE = date(2026, 8, 9)


# ==========================================
# DOMAINS
# ==========================================

DOMAINS = [
    "FRM Part I"
]


# ==========================================
# FRM STRUCTURE
# ==========================================

FRM_STRUCTURE = {

    "Foundations of Risk Management": [
        # Los agregaremos después
    ],

    "Quantitative Analysis": [

        "Fundamentals of Probability",

        "Random Variables",

        "Common Univariate Random Variables",

        "Multivariate Random Variables",

        "Sample Moments",

        "Hypothesis Testing",

        "Linear Regression",

        "Regression with Multiple Explanatory Variables",

        "Regression Diagnostics",

        "Stationary Time Series",

        "Nonstationary Time Series",

        "Measuring Return, Volatility, and Correlation",

        "Simulation and Bootstrapping",

        "Machine-Learning Methods",

        "Machine Learning and Prediction"

    ],

    "Financial Markets and Products": [
        # Los agregaremos después
    ],

    "Valuation and Risk Models": [
        # Los agregaremos después
    ]
}