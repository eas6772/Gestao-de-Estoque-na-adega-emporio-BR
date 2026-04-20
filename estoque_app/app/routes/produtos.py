from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.extensions import db
from app.models.models import Produto, Categoria
from app.utils import requer_admin

produtos_bp = Blueprint('produtos', __name__)

POR_PAGINA = 15


# ── Categorias ──────────────────────────────────────────────

@produtos_bp.route('/categorias')
@login_required
def categorias():
    cats = Categoria.query.order_by(Categoria.nome).all()
    return render_template('produtos/categorias.html', categorias=cats)


@produtos_bp.route('/categoria/nova', methods=['GET', 'POST'])
@login_required
@requer_admin
def nova_categoria():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        if not nome:
            flash('O nome da categoria é obrigatório.', 'warning')
        elif Categoria.query.filter_by(nome=nome).first():
            flash('Já existe uma categoria com este nome.', 'warning')
        else:
            db.session.add(Categoria(nome=nome))
            db.session.commit()
            flash(f'Categoria "{nome}" criada com sucesso.', 'success')
            return redirect(url_for('produtos.categorias'))

    return render_template('produtos/categorias.html',
                           categorias=Categoria.query.order_by(Categoria.nome).all(),
                           modo_form=True)


@produtos_bp.route('/categoria/<int:id>/editar', methods=['POST'])
@login_required
@requer_admin
def editar_categoria(id):
    cat = Categoria.query.get_or_404(id)
    nome = request.form.get('nome', '').strip()
    if not nome:
        flash('O nome não pode ser vazio.', 'warning')
    elif Categoria.query.filter(Categoria.nome == nome, Categoria.id != id).first():
        flash('Já existe uma categoria com este nome.', 'warning')
    else:
        cat.nome = nome
        db.session.commit()
        flash('Categoria atualizada.', 'success')
    return redirect(url_for('produtos.categorias'))


@produtos_bp.route('/categoria/<int:id>/toggle', methods=['POST'])
@login_required
@requer_admin
def toggle_categoria(id):
    cat = Categoria.query.get_or_404(id)
    cat.ativo = not cat.ativo
    db.session.commit()
    estado = 'ativada' if cat.ativo else 'desativada'
    flash(f'Categoria "{cat.nome}" {estado}.', 'info')
    return redirect(url_for('produtos.categorias'))


# ── Produtos ────────────────────────────────────────────────

@produtos_bp.route('/produtos')
@login_required
def lista_produtos():
    busca = request.args.get('q', '').strip()
    categoria_id = request.args.get('categoria_id', type=int)
    so_ativos = request.args.get('so_ativos', '1')
    pagina = request.args.get('pagina', 1, type=int)

    query = Produto.query

    if so_ativos == '1':
        query = query.filter_by(ativo=True)
    if categoria_id:
        query = query.filter_by(categoria_id=categoria_id)
    if busca:
        query = query.filter(
            db.or_(
                Produto.nome.ilike(f'%{busca}%'),
                Produto.fabricante.ilike(f'%{busca}%'),
                Produto.codigo_barras.ilike(f'%{busca}%'),
            )
        )

    paginacao = query.order_by(Produto.nome).paginate(page=pagina, per_page=POR_PAGINA, error_out=False)
    categorias = Categoria.query.filter_by(ativo=True).order_by(Categoria.nome).all()

    return render_template(
        'produtos/lista.html',
        paginacao=paginacao,
        categorias=categorias,
        busca=busca,
        categoria_id=categoria_id,
        so_ativos=so_ativos,
    )


@produtos_bp.route('/produto/novo', methods=['GET', 'POST'])
@login_required
@requer_admin
def novo_produto():
    categorias = Categoria.query.filter_by(ativo=True).order_by(Categoria.nome).all()

    if request.method == 'POST':
        produto, erros = _produto_do_form(request.form)
        if erros:
            for e in erros:
                flash(e, 'warning')
            return render_template('produtos/form.html', categorias=categorias, form=request.form)

        db.session.add(produto)
        db.session.commit()
        flash(f'Produto "{produto.nome}" cadastrado com sucesso.', 'success')
        return redirect(url_for('produtos.lista_produtos'))

    return render_template('produtos/form.html', categorias=categorias, form={})


@produtos_bp.route('/produto/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_admin
def editar_produto(id):
    produto = Produto.query.get_or_404(id)
    categorias = Categoria.query.filter_by(ativo=True).order_by(Categoria.nome).all()

    if request.method == 'POST':
        _, erros = _produto_do_form(request.form, produto)
        if erros:
            for e in erros:
                flash(e, 'warning')
            return render_template('produtos/form.html', produto=produto,
                                   categorias=categorias, form=request.form)

        db.session.commit()
        flash(f'Produto "{produto.nome}" atualizado.', 'success')
        return redirect(url_for('produtos.lista_produtos'))

    return render_template('produtos/form.html', produto=produto,
                           categorias=categorias, form=produto)


@produtos_bp.route('/produto/<int:id>/toggle', methods=['POST'])
@login_required
@requer_admin
def toggle_produto(id):
    produto = Produto.query.get_or_404(id)
    produto.ativo = not produto.ativo
    db.session.commit()
    estado = 'ativado' if produto.ativo else 'desativado'
    flash(f'Produto "{produto.nome}" {estado}.', 'info')
    return redirect(url_for('produtos.lista_produtos'))


# ── Helpers ─────────────────────────────────────────────────

def _produto_do_form(form, produto=None):
    erros = []
    nome = form.get('nome', '').strip()
    if not nome:
        erros.append('O nome do produto é obrigatório.')

    try:
        categoria_id = int(form.get('categoria_id', 0))
        if not Categoria.query.get(categoria_id):
            erros.append('Categoria inválida.')
    except (ValueError, TypeError):
        categoria_id = None
        erros.append('Categoria inválida.')

    try:
        preco_custo = float(form.get('preco_custo', 0))
        if preco_custo < 0:
            erros.append('Preço de custo não pode ser negativo.')
    except ValueError:
        preco_custo = 0
        erros.append('Preço de custo inválido.')

    try:
        margem_lucro = float(form.get('margem_lucro', 30))
        if margem_lucro < 0:
            erros.append('Margem de lucro não pode ser negativa.')
    except ValueError:
        margem_lucro = 30
        erros.append('Margem de lucro inválida.')

    try:
        estoque_minimo = int(form.get('estoque_minimo', 5))
        estoque_maximo = int(form.get('estoque_maximo', 100))
        if estoque_minimo < 0 or estoque_maximo < 0:
            erros.append('Estoques não podem ser negativos.')
        if estoque_maximo < estoque_minimo:
            erros.append('Estoque máximo deve ser maior que o mínimo.')
    except ValueError:
        estoque_minimo, estoque_maximo = 5, 100
        erros.append('Valores de estoque inválidos.')

    if erros:
        return None, erros

    if produto is None:
        produto = Produto()

    produto.nome = nome
    produto.categoria_id = categoria_id
    produto.fabricante = form.get('fabricante', '').strip() or None
    produto.volume = form.get('volume', '').strip() or None
    produto.peso = form.get('peso', '').strip() or None
    produto.codigo_barras = form.get('codigo_barras', '').strip() or None
    produto.margem_lucro = margem_lucro
    produto.preco_custo = preco_custo
    produto.estoque_minimo = estoque_minimo
    produto.estoque_maximo = estoque_maximo
    produto.calcular_preco_venda()

    return produto, []
