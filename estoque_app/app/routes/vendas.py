import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.models import Produto, Lote, Venda, ItemVenda, Movimentacao

vendas_bp = Blueprint('vendas', __name__)

POR_PAGINA = 20


# ── PDV ─────────────────────────────────────────────────────

@vendas_bp.route('/venda/nova', methods=['GET', 'POST'])
@login_required
def nova_venda():
    if request.method == 'POST':
        try:
            itens = json.loads(request.form.get('itens_json', '[]'))
        except (ValueError, TypeError):
            flash('Dados do carrinho inválidos.', 'danger')
            return redirect(url_for('vendas.nova_venda'))

        if not itens:
            flash('Adicione pelo menos um produto à venda.', 'warning')
            return redirect(url_for('vendas.nova_venda'))

        try:
            venda = Venda(usuario_id=current_user.id, total=0.0)
            db.session.add(venda)
            db.session.flush()

            total = 0.0
            for item_data in itens:
                produto_id = int(item_data['produto_id'])
                lote_id = int(item_data['lote_id'])
                qtd = int(item_data['quantidade'])

                produto = db.session.get(Produto, produto_id)
                if not produto or not produto.ativo:
                    raise ValueError('Produto inválido ou inativo.')

                lote = db.session.get(Lote, lote_id)
                if not lote or lote.produto_id != produto_id:
                    raise ValueError(f'Lote inválido para "{produto.nome}".')
                if lote.vencido:
                    raise ValueError(
                        f'Lote #{lote_id} de "{produto.nome}" está vencido.'
                    )
                if qtd > lote.quantidade:
                    raise ValueError(
                        f'Estoque insuficiente no lote #{lote_id} de "{produto.nome}" '
                        f'(disponível: {lote.quantidade}, solicitado: {qtd}).'
                    )

                lote.quantidade -= qtd

                db.session.add(ItemVenda(
                    venda_id=venda.id,
                    produto_id=produto_id,
                    lote_id=lote_id,
                    quantidade=qtd,
                    preco_unitario=produto.preco_venda,
                ))
                db.session.add(Movimentacao(
                    produto_id=produto_id,
                    lote_id=lote_id,
                    tipo='saida',
                    quantidade=qtd,
                    usuario_id=current_user.id,
                    motivo=f'Venda #{venda.id}',
                ))

                total += produto.preco_venda * qtd

            venda.total = round(total, 2)
            db.session.commit()
            flash(f'Venda #{venda.id} registrada! Total: R$ {venda.total:.2f}', 'success')
            return redirect(url_for('vendas.recibo', id=venda.id))

        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'danger')
            return redirect(url_for('vendas.nova_venda'))
        except Exception:
            db.session.rollback()
            flash('Erro ao registrar a venda. Tente novamente.', 'danger')
            return redirect(url_for('vendas.nova_venda'))

    return render_template('vendas/nova_venda.html')


# ── Recibo ───────────────────────────────────────────────────

@vendas_bp.route('/venda/<int:id>/recibo')
@login_required
def recibo(id):
    venda = db.session.get(Venda, id)
    if not venda:
        abort(404)
    return render_template('vendas/recibo.html', venda=venda)


# ── Histórico ────────────────────────────────────────────────

@vendas_bp.route('/vendas')
@login_required
def historico():
    pagina = request.args.get('pagina', 1, type=int)
    data_ini = request.args.get('data_ini', '')
    data_fim = request.args.get('data_fim', '')

    from datetime import datetime
    query = Venda.query.order_by(Venda.data.desc())

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

    paginacao = query.paginate(page=pagina, per_page=POR_PAGINA, error_out=False)
    return render_template(
        'vendas/historico.html',
        paginacao=paginacao,
        data_ini=data_ini,
        data_fim=data_fim,
    )


# ── API: busca de produto para o PDV (AJAX) ──────────────────

@vendas_bp.route('/venda/buscar-produto')
@login_required
def buscar_produto():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])

    produtos = (
        Produto.query
        .filter_by(ativo=True)
        .filter(db.or_(
            Produto.nome.ilike(f'%{q}%'),
            Produto.codigo_barras.ilike(f'%{q}%'),
            Produto.fabricante.ilike(f'%{q}%'),
        ))
        .order_by(Produto.nome)
        .limit(10)
        .all()
    )

    return jsonify([
        {
            'id': p.id,
            'nome': p.nome,
            'fabricante': p.fabricante or '',
            'preco_venda': p.preco_venda,
            'estoque': p.estoque_atual,
            'codigo_barras': p.codigo_barras or '',
        }
        for p in produtos
    ])
