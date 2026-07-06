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
        "The Building Blocks of Risk Management",
        "How Do Firms Manage Financial Risk?",
        "The Governance of Risk Management",
        "Credit Risk Transfer Mechanisms",
        "Modern Portfolio Theory (MPT) and the Capital Asset Pricing Model (CAPM)",
        "The Arbitrage Pricing Theory and Multifactor Models of Risk and Return",
        "Principles for Effective Risk Data Aggregation and Risk Reporting",
        "Enterprise Risk Management and Future Trends",
        "Learning From Financial Disasters",
        "Anatomy of the Great Financial Crisis of 2007-2009",
        "GARP Code of Conduct"
    ]
,

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
        "Banks",
        "Insurance Companies and Pension Plans",
        "Fund Management",
        "Introduction to Derivatives",
        "Exchanges and OTC Markets",
        "Central Clearing",
        "Futures Markets",
        "Using Futures for Hedging",
        "Foreign Exchange Markets",
        "Pricing Financial Forwards and Futures",
        "Commodity Forwards and Futures",
        "Options Markets",
        "Properties of Options",
        "Trading Strategies",
        "Exotic Options",
        "Properties of Interest Rates",
        "Corporate Bonds",
        "Mortgages and Mortgage-Backed Securities",
        "Interest Rate Futures",
        "Swaps"
    ],

        "Valuation and Risk Models": [
        "Measures of Financial Risk",
        "Calculating and Applying VaR",
        "Measuring and Monitoring Volatility",
        "External and Internal Credit Ratings",
        "Country Risk",
        "Measuring Credit Risk",
        "Operational Risk",
        "Stress Testing",
        "Pricing Conventions, Discounting, and Arbitrage",
        "Interest Rates",
        "Bond Yields and Return Calculations",
        "Applying Duration, Convexity, and DV01",
        "Modeling and Hedging Non-Parallel Term Structure Shifts",
        "Binomial Trees",
        "The Black-Scholes-Merton Model",
        "Option Sensitivity Measures: The “Greeks”"
    ]

}