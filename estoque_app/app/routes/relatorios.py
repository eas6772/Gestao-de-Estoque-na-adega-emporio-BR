from datetime import datetime
from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import func
from app.extensions import db
from app.models.models import Produto, Movimentacao, Venda, ItemVenda

relatorios_bp = Blueprint('relatorios', __name__)

POR_PAGINA = 30


@relatorios_bp.route('/relatorios/estoque')
@login_required
def relatorio_estoque():
    produtos = (
        Produto.query
        .filter_by(ativo=True)
        .order_by(Produto.nome)
        .all()
    )
    total_estoque = sum(p.estoque_atual * p.preco_custo for p in produtos)
    return render_template('relatorios/estoque.html', produtos=produtos, total_estoque=total_estoque)


@relatorios_bp.route('/relatorios/mais-vendidos')
@login_required
def mais_vendidos():
    data_ini = request.args.get('data_ini', '')
    data_fim = request.args.get('data_fim', '')

    query = (
        db.session.query(
            Produto.id,
            Produto.nome,
            Produto.fabricante,
            func.sum(ItemVenda.quantidade).label('qtd_vendida'),
            func.sum(ItemVenda.quantidade * ItemVenda.preco_unitario).label('receita'),
        )
        .join(ItemVenda, ItemVenda.produto_id == Produto.id)
        .join(Venda, Venda.id == ItemVenda.venda_id)
        .group_by(Produto.id)
        .order_by(func.sum(ItemVenda.quantidade).desc())
    )

    if data_ini:
        try:
            query = query.filter(Venda.data >= datetime.fromisoformat(data_ini))
        except ValueError:
            pass
    if data_fim:
        try:
            query = query.filter(Venda.data <= datetime.fromisoformat(data_fim + 'T23:59:59'))
        except ValueError:
            pass

    resultados = query.limit(20).all()
    receita_total = sum(r.receita for r in resultados)
    unidades_total = sum(r.qtd_vendida for r in resultados)

    return render_template(
        'relatorios/mais_vendidos.html',
        resultados=resultados,
        receita_total=receita_total,
        unidades_total=unidades_total,
        data_ini=data_ini,
        data_fim=data_fim,
    )


@relatorios_bp.route('/relatorios/movimentacoes')
@login_required
def relatorio_movimentacoes():
    pagina = request.args.get('pagina', 1, type=int)
    data_ini = request.args.get('data_ini', '')
    data_fim = request.args.get('data_fim', '')
    tipo = request.args.get('tipo', '')

    query = Movimentacao.query.order_by(Movimentacao.data.desc())

    if data_ini:
        try:
            query = query.filter(Movimentacao.data >= datetime.fromisoformat(data_ini))
        except ValueError:
            pass
    if data_fim:
        try:
            query = query.filter(Movimentacao.data <= datetime.fromisoformat(data_fim + 'T23:59:59'))
        except ValueError:
            pass
    if tipo in ('entrada', 'saida', 'ajuste'):
        query = query.filter_by(tipo=tipo)

    paginacao = query.paginate(page=pagina, per_page=POR_PAGINA, error_out=False)
    return render_template(
        'relatorios/movimentacoes.html',
        paginacao=paginacao,
        data_ini=data_ini,
        data_fim=data_fim,
        tipo=tipo,
    )


@relatorios_bp.route('/relatorios/lucro')
@login_required
def relatorio_lucro():
    data_ini = request.args.get('data_ini', '')
    data_fim = request.args.get('data_fim', '')

    query = (
        db.session.query(
            Produto.id,
            Produto.nome,
            Produto.fabricante,
            Produto.preco_custo,
            func.sum(ItemVenda.quantidade).label('qtd_vendida'),
            func.sum(ItemVenda.quantidade * ItemVenda.preco_unitario).label('receita'),
            func.sum(ItemVenda.quantidade * Produto.preco_custo).label('custo_total'),
        )
        .join(ItemVenda, ItemVenda.produto_id == Produto.id)
        .join(Venda, Venda.id == ItemVenda.venda_id)
        .group_by(Produto.id)
        .order_by(func.sum(ItemVenda.quantidade * ItemVenda.preco_unitario).desc())
    )

    if data_ini:
        try:
            query = query.filter(Venda.data >= datetime.fromisoformat(data_ini))
        except ValueError:
            pass
    if data_fim:
        try:
            query = query.filter(Venda.data <= datetime.fromisoformat(data_fim + 'T23:59:59'))
        except ValueError:
            pass

    resultados = query.all()
    lucro_total = sum(r.receita - r.custo_total for r in resultados)
    receita_total = sum(r.receita for r in resultados)

    return render_template(
        'relatorios/lucro.html',
        resultados=resultados,
        lucro_total=lucro_total,
        receita_total=receita_total,
        data_ini=data_ini,
        data_fim=data_fim,
    )


@relatorios_bp.route('/relatorios/reposicao')
@login_required
def relatorio_reposicao():
    produtos = (
        Produto.query
        .filter_by(ativo=True)
        .order_by(Produto.nome)
        .all()
    )
    reposicao = [p for p in produtos if p.estoque_atual <= p.estoque_minimo]
    return render_template('relatorios/reposicao.html', produtos=reposicao)
