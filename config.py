import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # --- Core ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deploying")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'nashe.db')}"
    )
    # Render/Heroku give postgres:// -- SQLAlchemy 1.4+ needs postgresql://
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Uploads ---
    UPLOAD_FOLDER = os.path.join(basedir, "static", "uploads")
    PRODUCT_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, "products")
    POST_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, "posts")
    PROOF_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, "proofs")
    MAX_CONTENT_LENGTH = 12 * 1024 * 1024  # 12MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "mp4", "mov"}

    # --- Admin ---
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme123")
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

    # --- Business info ---
    WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "265999000000")  # no + or spaces
    STORE_NAME = "Nashe Designs"
    STORE_TAGLINE = "Apparel and Clothing"
    USD_TO_MWK_RATE = float(os.environ.get("USD_TO_MWK_RATE", "1750"))

    # --- Payments (fill in real credentials before going live) ---
    AIRTEL_MONEY_NUMBER = os.environ.get("AIRTEL_MONEY_NUMBER", "265999000000")
    TNM_MPAMBA_NUMBER = os.environ.get("TNM_MPAMBA_NUMBER", "265888000000")
    BANK_NAME = os.environ.get("BANK_NAME", "National Bank of Malawi")
    BANK_ACCOUNT_NAME = os.environ.get("BANK_ACCOUNT_NAME", "Nashe Designs")
    BANK_ACCOUNT_NUMBER = os.environ.get("BANK_ACCOUNT_NUMBER", "0000000000")
    PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
    STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    BINANCE_PAY_ID = os.environ.get("BINANCE_PAY_ID", "000000000")
    USDT_WALLET_ADDRESS = os.environ.get("USDT_WALLET_ADDRESS", "TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")

    # --- AI chatbot ---
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    CHATBOT_MODEL = os.environ.get("CHATBOT_MODEL", "claude-sonnet-5")
