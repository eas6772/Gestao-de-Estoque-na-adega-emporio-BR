from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.models import Usuario, Movimentacao

usuarios_bp = Blueprint('usuarios', __name__)


def _somente_admin():
    if not current_user.is_admin:
        flash('Acesso restrito ao administrador.', 'danger')
        return redirect(url_for('main.dashboard'))
    return None


@usuarios_bp.route('/usuarios')
@login_required
def lista_usuarios():
    bloqueio = _somente_admin()
    if bloqueio:
        return bloqueio
    usuarios = Usuario.query.order_by(Usuario.nome).all()
    return render_template('usuarios/lista.html', usuarios=usuarios)


@usuarios_bp.route('/usuarios/novo', methods=['GET', 'POST'])
@login_required
def novo_usuario():
    bloqueio = _somente_admin()
    if bloqueio:
        return bloqueio

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        senha = request.form.get('senha', '')
        perfil = request.form.get('perfil', 'operador')

        if not nome or not senha:
            flash('Nome e senha são obrigatórios.', 'warning')
            return render_template('usuarios/form.html', usuario=None, acao='novo')

        if len(senha) < 6:
            flash('A senha deve ter no mínimo 6 caracteres.', 'warning')
            return render_template('usuarios/form.html', usuario=None, acao='novo')

        if Usuario.query.filter_by(nome=nome).first():
            flash('Já existe um usuário com esse nome.', 'warning')
            return render_template('usuarios/form.html', usuario=None, acao='novo')

        u = Usuario(nome=nome, perfil=perfil)
        u.set_senha(senha)
        db.session.add(u)
        db.session.commit()
        flash(f'Usuário "{nome}" criado com sucesso.', 'success')
        return redirect(url_for('usuarios.lista_usuarios'))

    return render_template('usuarios/form.html', usuario=None, acao='novo')


@usuarios_bp.route('/usuarios/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    bloqueio = _somente_admin()
    if bloqueio:
        return bloqueio

    u = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        perfil = request.form.get('perfil', 'operador')
        if perfil not in ('admin', 'operador'):
            perfil = 'operador'
        nova_senha = request.form.get('senha', '')

        if not nome:
            flash('O nome é obrigatório.', 'warning')
            return render_template('usuarios/form.html', usuario=u, acao='editar')

        existente = Usuario.query.filter_by(nome=nome).first()
        if existente and existente.id != u.id:
            flash('Já existe um usuário com esse nome.', 'warning')
            return render_template('usuarios/form.html', usuario=u, acao='editar')

        # Impede que o admin remova seu próprio perfil de admin
        if u.id == current_user.id and perfil != 'admin':
            flash('Você não pode remover seu próprio perfil de administrador.', 'warning')
            return render_template('usuarios/form.html', usuario=u, acao='editar')

        u.nome = nome
        u.perfil = perfil

        if nova_senha:
            if len(nova_senha) < 6:
                flash('A nova senha deve ter no mínimo 6 caracteres.', 'warning')
                return render_template('usuarios/form.html', usuario=u, acao='editar')
            u.set_senha(nova_senha)

        db.session.commit()
        flash(f'Usuário "{u.nome}" atualizado.', 'success')
        return redirect(url_for('usuarios.lista_usuarios'))

    return render_template('usuarios/form.html', usuario=u, acao='editar')


@usuarios_bp.route('/admin/movimentacoes/purge', methods=['GET', 'POST'])
@login_required
def purge_movimentacoes():
    bloqueio = _somente_admin()
    if bloqueio:
        return bloqueio

    total_preview = None
    data_inicio_str = ''
    data_fim_str = ''

    if request.method == 'POST':
        data_inicio_str = request.form.get('data_inicio', '').strip()
        data_fim_str   = request.form.get('data_fim', '').strip()
        acao           = request.form.get('acao', 'preview')

        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d')
            data_fim    = datetime.strptime(data_fim_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        except ValueError:
            flash('Datas inválidas. Use o formato correto.', 'warning')
            return render_template('usuarios/purge_movimentacoes.html',
                                   total_preview=None,
                                   data_inicio=data_inicio_str,
                                   data_fim=data_fim_str)

        if data_inicio > data_fim:
            flash('A data inicial deve ser anterior ou igual à data final.', 'warning')
            return render_template('usuarios/purge_movimentacoes.html',
                                   total_preview=None,
                                   data_inicio=data_inicio_str,
                                   data_fim=data_fim_str)

        query = Movimentacao.query.filter(
            Movimentacao.data >= data_inicio,
            Movimentacao.data <= data_fim
        )

        if acao == 'preview':
            total_preview = query.count()
        elif acao == 'confirmar':
            total = query.count()
            if total == 0:
                flash('Nenhuma movimentação encontrada no período informado.', 'info')
            else:
                query.delete(synchronize_session=False)
                db.session.commit()
                flash(f'{total} movimentação(ões) excluída(s) com sucesso.', 'success')
            return redirect(url_for('usuarios.purge_movimentacoes'))

    return render_template('usuarios/purge_movimentacoes.html',
                           total_preview=total_preview,
                           data_inicio=data_inicio_str,
                           data_fim=data_fim_str)


@usuarios_bp.route('/usuarios/<int:id>/toggle-ativo', methods=['POST'])
@login_required
def toggle_ativo(id):
    bloqueio = _somente_admin()
    if bloqueio:
        return bloqueio

    u = Usuario.query.get_or_404(id)

    if u.id == current_user.id:
        flash('Você não pode desativar sua própria conta.', 'warning')
        return redirect(url_for('usuarios.lista_usuarios'))

    u.ativo = not u.ativo
    db.session.commit()
    estado = 'ativado' if u.ativo else 'desativado'
    flash(f'Usuário "{u.nome}" {estado}.', 'success')
    return redirect(url_for('usuarios.lista_usuarios'))
