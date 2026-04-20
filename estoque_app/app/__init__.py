from flask import Flask
from config import config
from app.extensions import db, login_manager, migrate


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    from app.models import models  # noqa: F401 — necessário para o Flask-Migrate detectar os modelos

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.produtos import produtos_bp
    from app.routes.estoque import estoque_bp
    from app.routes.vendas import vendas_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(produtos_bp)
    app.register_blueprint(estoque_bp)
    app.register_blueprint(vendas_bp)

    return app
