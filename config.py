"""
Central configuration module.
Keeps all LLM / app configuration in one place so it is easy to change later.
"""
import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "boardroom.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    # NOTE: "gemini-2.0-flash" was retired by Google on 1 June 2026 and now
    # returns a 404 "model not found" error, which is what was causing every
    # agent page to render blank/failed. "gemini-2.5-flash" is the current
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    # Setting thinking budget to 0 disables internal reasoning tokens,
    # accelerating structured output generation by 3x-5x per agent call.
    GEMINI_THINKING_BUDGET = int(os.environ.get("GEMINI_THINKING_BUDGET", "0"))
    GEMINI_MAX_RETRIES = int(os.environ.get("GEMINI_MAX_RETRIES", "5"))

    # Weighted scoring configuration (must sum to 1.0)
    SCORE_WEIGHTS = {
        "finance": 0.25,
        "marketing": 0.20,
        "operations": 0.20,
        "risk": 0.20,
        "strategic_fit": 0.15,
    }

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
