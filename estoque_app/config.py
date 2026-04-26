import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Em dev gera chave aleatória segura; em prod definir SECRET_KEY via env var.
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(32))

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Cookies de sessão seguros
    SESSION_COOKIE_HTTPONLY    = True
    SESSION_COOKIE_SAMESITE    = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

    WTF_CSRF_TIME_LIMIT = 3600


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False   # HTTP ok em localhost
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'database.db')}"
    )


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True    # exige HTTPS

    _db_url = os.environ.get('DATABASE_URL', '')
    # Render.com retorna postgres:// — SQLAlchemy exige postgresql://
    SQLALCHEMY_DATABASE_URI = _db_url.replace('postgres://', 'postgresql://', 1) or None


config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}
