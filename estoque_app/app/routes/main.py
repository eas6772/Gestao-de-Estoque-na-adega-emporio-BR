from datetime import date, timedelta, datetime, timezone
from flask import Blueprint, render_template
from flask_login import login_required
from app.extensions import db
from app.models.models import Produto, Lote, Venda

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    hoje = date.today()
    limite_vencimento = hoje + timedelta(days=30)
    inicio_dia = datetime.combine(hoje, datetime.min.time()).replace(tzinfo=timezone.utc)

    total_produtos = Produto.query.filter_by(ativo=True).count()

    # Produtos ativos com estoque abaixo do mínimo
    produtos_ativos = Produto.query.filter_by(ativo=True).all()
    alertas_estoque = [p for p in produtos_ativos if p.estoque_atual <= p.estoque_minimo]

    # Lotes válidos que vencem em até 30 dias
    lotes_vencendo = (
        Lote.query
        .filter(Lote.data_validade != None)
        .filter(Lote.data_validade >= hoje)
        .filter(Lote.data_validade <= limite_vencimento)
        .filter(Lote.quantidade > 0)
        .order_by(Lote.data_validade.asc())
        .all()
    )

    # Total vendido hoje (soma dos totais das vendas do dia)
    vendas_hoje = Venda.query.filter(Venda.data >= inicio_dia).all()
    total_vendas_hoje = sum(v.total for v in vendas_hoje)

    return render_template(
        'main/dashboard.html',
        total_produtos=total_produtos,
        alertas_estoque=alertas_estoque,
        lotes_vencendo=lotes_vencendo,
        total_vendas_hoje=total_vendas_hoje,
        qtd_vendas_hoje=len(vendas_hoje),
        hoje=hoje,
    )
