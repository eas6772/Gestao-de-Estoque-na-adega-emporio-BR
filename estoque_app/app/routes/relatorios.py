import io
from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, request, make_response, abort
from flask_login import login_required, current_user


def requer_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated
from sqlalchemy import func
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
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
@requer_admin
def mais_vendidos():
    data_ini = request.args.get('data_ini', '')
    data_fim = request.args.get('data_fim', '')
    pagina = request.args.get('pagina', 1, type=int)

    query = (
        db.session.query(
            Produto.id,
            Produto.nome,
            Produto.fabricante,
            func.sum(ItemVenda.quantidade).label('qtd_vendida'),
            func.sum(ItemVenda.quantidade *
                     ItemVenda.preco_unitario).label('receita'),
        )
        .join(ItemVenda, ItemVenda.produto_id == Produto.id)
        .join(Venda, Venda.id == ItemVenda.venda_id)
        .group_by(Produto.id)
        .order_by(func.sum(ItemVenda.quantidade).desc())
    )

    if data_ini:
        try:
            query = query.filter(
                Venda.data >= datetime.fromisoformat(data_ini))
        except ValueError:
            pass
    if data_fim:
        try:
            query = query.filter(
                Venda.data <= datetime.fromisoformat(data_fim + 'T23:59:59'))
        except ValueError:
            pass

    todos = query.all()
    receita_total = sum(r.receita for r in todos)
    unidades_total = sum(r.qtd_vendida for r in todos)

    paginacao = query.paginate(page=pagina, per_page=POR_PAGINA, error_out=False)
    resultados = paginacao.items

    return render_template(
        'relatorios/mais_vendidos.html',
        paginacao=paginacao,
        resultados=resultados,
        receita_total=receita_total,
        unidades_total=unidades_total,
        data_ini=data_ini,
        data_fim=data_fim,
    )


@relatorios_bp.route('/relatorios/mais-vendidos/pdf')
@login_required
def mais_vendidos_pdf():
    # Busca apenas produtos ativos com estoque <= estoque_minimo
    todos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    produtos = [p for p in todos if p.estoque_atual <= p.estoque_minimo]

    # Gera PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2.5 * cm,
    )

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        'titulo',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=4,
    )
    style_subtitle = ParagraphStyle(
        'subtitulo',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#555555'),
        spaceAfter=2,
    )
    style_footnote = ParagraphStyle(
        'rodape',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#777777'),
        leftIndent=0,
    )

    elementos = []

    # Cabeçalho
    elementos.append(
        Paragraph('Empório BR — Lista de Reposição de Estoque', style_title))
    elementos.append(
        Paragraph('Baseado nos Produtos com Estoque abaixo do mínimo', style_subtitle))
    elementos.append(Paragraph(
        f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}', style_subtitle))
    elementos.append(Spacer(1, 0.5 * cm))

    # Tabela
    cabecalho = ['Produto', 'Fabricante',
                 'Qtd. para Compra', 'Custo de Reposição']
    linhas = [cabecalho]

    for p in produtos:
        qtd_compra = max(p.estoque_maximo - p.estoque_atual, 0)
        custo_reposicao = qtd_compra * (p.preco_custo or 0)
        linhas.append([
            p.nome,
            p.fabricante or '—',
            str(qtd_compra),
            f'R$ {custo_reposicao:,.2f}'.replace(
                ',', 'X').replace('.', ',').replace('X', '.'),
        ])

    col_widths = [7 * cm, 4.5 * cm, 3.5 * cm, 4 * cm]
    tabela = Table(linhas, colWidths=col_widths, repeatRows=1)
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.HexColor('#f9f9f9'), colors.white]),
        ('ALIGN', (2, 1), (3, -1), 'CENTER'),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor('#22c55e')),
    ]))

    elementos.append(tabela)

    # Total
    total_custo = sum(
        max(p.estoque_maximo - p.estoque_atual, 0) * (p.preco_custo or 0)
        for p in produtos
    )
    elementos.append(Spacer(1, 0.3 * cm))
    elementos.append(Paragraph(
        f'<b>Custo total estimado de reposição: R$ {total_custo:,.2f}</b>'.replace(
            ',', 'X').replace('.', ',').replace('X', '.'),
        ParagraphStyle('total', parent=styles['Normal'], fontSize=10, alignment=TA_RIGHT,
                       textColor=colors.HexColor('#1a1a2e')),
    ))

    # Nota de rodapé
    elementos.append(Spacer(1, 0.6 * cm))
    elementos.append(Paragraph(
        '* O custo estimado foi baseado no último Preço de Custo de cada Produto.',
        style_footnote,
    ))

    doc.build(elementos)
    buffer.seek(0)

    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    response.headers[
        'Content-Disposition'] = f'attachment; filename=ordem_reposicao_{timestamp}.pdf'
    return response


@relatorios_bp.route('/relatorios/movimentacoes')
@login_required
@requer_admin
def relatorio_movimentacoes():
    pagina = request.args.get('pagina', 1, type=int)
    data_ini = request.args.get('data_ini', '')
    data_fim = request.args.get('data_fim', '')
    tipo = request.args.get('tipo', '')

    query = Movimentacao.query.order_by(Movimentacao.data.desc())

    if data_ini:
        try:
            query = query.filter(Movimentacao.data >=
                                 datetime.fromisoformat(data_ini))
        except ValueError:
            pass
    if data_fim:
        try:
            query = query.filter(
                Movimentacao.data <= datetime.fromisoformat(data_fim + 'T23:59:59'))
        except ValueError:
            pass
    if tipo in ('entrada', 'saida', 'ajuste'):
        query = query.filter_by(tipo=tipo)

    paginacao = query.paginate(
        page=pagina, per_page=POR_PAGINA, error_out=False)
    return render_template(
        'relatorios/movimentacoes.html',
        paginacao=paginacao,
        data_ini=data_ini,
        data_fim=data_fim,
        tipo=tipo,
    )


@relatorios_bp.route('/relatorios/lucro')
@login_required
@requer_admin
def relatorio_lucro():
    data_ini = request.args.get('data_ini', '')
    data_fim = request.args.get('data_fim', '')
    pagina = request.args.get('pagina', 1, type=int)

    query = (
        db.session.query(
            Produto.id,
            Produto.nome,
            Produto.fabricante,
            Produto.preco_custo,
            func.sum(ItemVenda.quantidade).label('qtd_vendida'),
            func.sum(ItemVenda.quantidade *
                     ItemVenda.preco_unitario).label('receita'),
            func.sum(ItemVenda.quantidade *
                     Produto.preco_custo).label('custo_total'),
        )
        .join(ItemVenda, ItemVenda.produto_id == Produto.id)
        .join(Venda, Venda.id == ItemVenda.venda_id)
        .group_by(Produto.id)
        .order_by(func.sum(ItemVenda.quantidade * ItemVenda.preco_unitario).desc())
    )

    if data_ini:
        try:
            query = query.filter(
                Venda.data >= datetime.fromisoformat(data_ini))
        except ValueError:
            pass
    if data_fim:
        try:
            query = query.filter(
                Venda.data <= datetime.fromisoformat(data_fim + 'T23:59:59'))
        except ValueError:
            pass

    todos = query.all()
    lucro_total = sum(r.receita - r.custo_total for r in todos)
    receita_total = sum(r.receita for r in todos)

    paginacao = query.paginate(page=pagina, per_page=POR_PAGINA, error_out=False)

    return render_template(
        'relatorios/lucro.html',
        paginacao=paginacao,
        resultados=paginacao.items,
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
