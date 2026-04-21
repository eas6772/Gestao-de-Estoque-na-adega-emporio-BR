from datetime import date, datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.models import Produto, Lote, Movimentacao
from app.utils import requer_admin

estoque_bp = Blueprint('estoque', __name__)

POR_PAGINA = 20


# ── Visão Geral ─────────────────────────────────────────────

@estoque_bp.route('/estoque')
@login_required
def visao_geral():
    busca = request.args.get('q', '').strip()
    filtro = request.args.get('filtro', 'todos')  # 'todos', 'baixo', 'zerado'
    pagina = request.args.get('pagina', 1, type=int)

    query = Produto.query.filter_by(ativo=True)
    if busca:
        query = query.filter(Produto.nome.ilike(f'%{busca}%'))

    produtos = query.order_by(Produto.nome).all()

    # Filtro pós-query (depende de propriedade calculada)
    if filtro == 'baixo':
        produtos = [p for p in produtos if 0 < p.estoque_atual <= p.estoque_minimo]
    elif filtro == 'zerado':
        produtos = [p for p in produtos if p.estoque_atual == 0]

    # Paginação manual
    total = len(produtos)
    inicio = (pagina - 1) * POR_PAGINA
    fim = inicio + POR_PAGINA
    itens = produtos[inicio:fim]
    total_paginas = max(1, -(-total // POR_PAGINA))

    return render_template(
        'estoque/visao_geral.html',
        produtos=itens,
        total=total,
        pagina=pagina,
        total_paginas=total_paginas,
        busca=busca,
        filtro=filtro,
    )


# ── Entrada de Mercadoria ───────────────────────────────────

@estoque_bp.route('/estoque/entrada', methods=['GET', 'POST'])
@login_required
def entrada():
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()

    if request.method == 'POST':
        produto_id = request.form.get('produto_id', type=int)
        quantidade = request.form.get('quantidade', type=int)
        numero_lote = request.form.get('numero_lote', '').strip() or None
        data_validade_str = request.form.get('data_validade', '').strip()
        motivo = request.form.get('motivo', '').strip() or 'Entrada de estoque'

        erros = _validar_entrada(produto_id, quantidade)
        if erros:
            for e in erros:
                flash(e, 'warning')
            return render_template('estoque/entrada.html', produtos=produtos, form=request.form)

        data_validade = None
        if data_validade_str:
            try:
                data_validade = date.fromisoformat(data_validade_str)
            except ValueError:
                flash('Data de validade inválida.', 'warning')
                return render_template('estoque/entrada.html', produtos=produtos, form=request.form)

        lote = Lote(
            produto_id=produto_id,
            numero_lote=numero_lote,
            quantidade=quantidade,
            data_validade=data_validade,
        )
        db.session.add(lote)
        db.session.flush()

        mov = Movimentacao(
            produto_id=produto_id,
            lote_id=lote.id,
            tipo='entrada',
            quantidade=quantidade,
            usuario_id=current_user.id,
            motivo=motivo,
        )
        db.session.add(mov)
        db.session.commit()

        produto = Produto.query.get(produto_id)
        flash(f'Entrada de {quantidade} unidade(s) de "{produto.nome}" registrada.', 'success')
        return redirect(url_for('estoque.visao_geral'))

    produto_id_pre = request.args.get('produto_id', type=int)
    return render_template('estoque/entrada.html', produtos=produtos,
                           form={'produto_id': produto_id_pre or ''})


# ── Ajuste de Estoque ───────────────────────────────────────

@estoque_bp.route('/estoque/ajuste', methods=['GET', 'POST'])
@login_required
@requer_admin
def ajuste():
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()

    if request.method == 'POST':
        produto_id = request.form.get('produto_id', type=int)
        lote_id = request.form.get('lote_id', type=int)
        nova_qtd = request.form.get('nova_quantidade', type=int)
        motivo = request.form.get('motivo', '').strip()

        if not produto_id or nova_qtd is None or nova_qtd < 0:
            flash('Preencha todos os campos obrigatórios.', 'warning')
            return render_template('estoque/ajuste.html', produtos=produtos, form=request.form)

        lote = Lote.query.get_or_404(lote_id)
        if lote.produto_id != produto_id:
            flash('Lote não pertence ao produto selecionado.', 'danger')
            return render_template('estoque/ajuste.html', produtos=produtos, form=request.form)

        diferenca = nova_qtd - lote.quantidade
        lote.quantidade = nova_qtd

        mov = Movimentacao(
            produto_id=produto_id,
            lote_id=lote_id,
            tipo='ajuste',
            quantidade=diferenca,
            usuario_id=current_user.id,
            motivo=motivo or f'Ajuste manual: lote #{lote_id}',
        )
        db.session.add(mov)
        db.session.commit()

        produto = Produto.query.get(produto_id)
        flash(f'Estoque do lote #{lote_id} ({produto.nome}) ajustado para {nova_qtd}.', 'success')
        return redirect(url_for('estoque.visao_geral'))

    return render_template('estoque/ajuste.html', produtos=produtos, form={})


# ── Editar Validade de Lote ─────────────────────────────────

@estoque_bp.route('/estoque/lote/<int:lote_id>/validade', methods=['GET', 'POST'])
@login_required
@requer_admin
def editar_validade(lote_id):
    lote = Lote.query.get_or_404(lote_id)
    produto = lote.produto

    if request.method == 'POST':
        nova_validade_str = request.form.get('data_validade', '').strip()
        motivo = request.form.get('motivo', '').strip() or 'Correção de data de validade'

        nova_validade = None
        if nova_validade_str:
            try:
                nova_validade = date.fromisoformat(nova_validade_str)
            except ValueError:
                flash('Data de validade inválida.', 'warning')
                return render_template('estoque/editar_validade.html', lote=lote, produto=produto)

        lote.data_validade = nova_validade

        mov = Movimentacao(
            produto_id=produto.id,
            lote_id=lote.id,
            tipo='ajuste',
            quantidade=0,
            usuario_id=current_user.id,
            motivo=motivo,
        )
        db.session.add(mov)
        db.session.commit()

        flash(f'Validade do lote #{lote.id} ({produto.nome}) atualizada.', 'success')
        return redirect(url_for('estoque.visao_geral'))

    return render_template('estoque/editar_validade.html', lote=lote, produto=produto)


# ── Histórico de Movimentações ──────────────────────────────

@estoque_bp.route('/movimentacoes')
@login_required
def movimentacoes():
    busca = request.args.get('q', '').strip()
    tipo = request.args.get('tipo', '')
    data_ini = request.args.get('data_ini', '')
    data_fim = request.args.get('data_fim', '')
    pagina = request.args.get('pagina', 1, type=int)

    query = (
        Movimentacao.query
        .join(Produto, Movimentacao.produto_id == Produto.id)
        .order_by(Movimentacao.data.desc())
    )

    if busca:
        query = query.filter(Produto.nome.ilike(f'%{busca}%'))
    if tipo:
        query = query.filter(Movimentacao.tipo == tipo)
    if data_ini:
        try:
            query = query.filter(
                Movimentacao.data >= datetime.fromisoformat(data_ini)
            )
        except ValueError:
            pass
    if data_fim:
        try:
            query = query.filter(
                Movimentacao.data <= datetime.fromisoformat(data_fim + 'T23:59:59')
            )
        except ValueError:
            pass

    paginacao = query.paginate(page=pagina, per_page=POR_PAGINA, error_out=False)

    return render_template(
        'estoque/movimentacoes.html',
        paginacao=paginacao,
        busca=busca,
        tipo=tipo,
        data_ini=data_ini,
        data_fim=data_fim,
    )


# ── API interna: lotes de um produto (AJAX) ─────────────────

@estoque_bp.route('/estoque/lotes/<int:produto_id>')
@login_required
def lotes_produto(produto_id):
    """Retorna JSON com lotes válidos do produto para o formulário de ajuste."""
    from flask import jsonify
    hoje = date.today()
    lotes = (
        Lote.query
        .filter_by(produto_id=produto_id)
        .filter(Lote.quantidade > 0)
        .filter(
            db.or_(Lote.data_validade == None, Lote.data_validade >= hoje)
        )
        .order_by(Lote.data_validade.asc())
        .all()
    )
    return jsonify([
        {
            'id': l.id,
            'numero_lote': l.numero_lote or '',
            'quantidade': l.quantidade,
            'data_validade': l.data_validade.strftime('%d/%m/%Y') if l.data_validade else 'Sem validade',
            'data_entrada': l.data_entrada.strftime('%d/%m/%Y') if l.data_entrada else '',
        }
        for l in lotes
    ])


# ── Helpers ─────────────────────────────────────────────────

def _validar_entrada(produto_id, quantidade):
    erros = []
    if not produto_id:
        erros.append('Selecione um produto.')
    else:
        p = Produto.query.get(produto_id)
        if not p or not p.ativo:
            erros.append('Produto inválido ou inativo.')
    if not quantidade or quantidade <= 0:
        erros.append('A quantidade deve ser maior que zero.')
    return erros


def lotes_peps(produto_id):
    """Retorna lotes válidos e não vencidos ordenados por PEPS (validade mais próxima primeiro)."""
    hoje = date.today()
    return (
        Lote.query
        .filter_by(produto_id=produto_id)
        .filter(Lote.quantidade > 0)
        .filter(
            db.or_(Lote.data_validade == None, Lote.data_validade >= hoje)
        )
        .order_by(Lote.data_validade.asc().nullslast())
        .all()
    )
