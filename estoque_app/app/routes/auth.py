from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models.models import Usuario
from app.extensions import limiter

auth_bp = Blueprint('auth', __name__)


def _url_segura(url):
    """Aceita apenas redirecionamentos relativos (sem netloc), evitando open redirect."""
    if not url:
        return False
    parsed = urlparse(url)
    return not parsed.netloc and not parsed.scheme


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute; 30 per hour', methods=['POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        nome  = request.form.get('nome', '').strip()
        senha = request.form.get('senha', '')

        usuario = Usuario.query.filter_by(nome=nome, ativo=True).first()

        if usuario and usuario.verificar_senha(senha):
            login_user(usuario)
            proxima = request.args.get('next')
            return redirect(proxima if _url_segura(proxima) else url_for('main.dashboard'))

        flash('Usuário ou senha incorretos.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão encerrada com sucesso.', 'info')
    return redirect(url_for('auth.login'))
