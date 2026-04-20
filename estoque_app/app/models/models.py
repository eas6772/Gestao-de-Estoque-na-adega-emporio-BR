from datetime import datetime, date, timezone
from app.extensions import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(20), nullable=False, default='operador')  # 'admin' ou 'operador'
    ativo = db.Column(db.Boolean, default=True)

    movimentacoes = db.relationship('Movimentacao', backref='usuario', lazy='dynamic')
    vendas = db.relationship('Venda', backref='usuario', lazy='dynamic')

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    @property
    def is_admin(self):
        return self.perfil == 'admin'

    def __repr__(self):
        return f'<Usuario {self.nome}>'


class Categoria(db.Model):
    __tablename__ = 'categorias'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False, unique=True)
    ativo = db.Column(db.Boolean, default=True)

    produtos = db.relationship('Produto', backref='categoria', lazy='dynamic')

    def __repr__(self):
        return f'<Categoria {self.nome}>'


class Produto(db.Model):
    __tablename__ = 'produtos'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    fabricante = db.Column(db.String(100))
    volume = db.Column(db.String(30))
    peso = db.Column(db.String(30))
    codigo_barras = db.Column(db.String(50), unique=True)
    margem_lucro = db.Column(db.Float, nullable=False, default=30.0)
    preco_custo = db.Column(db.Float, nullable=False, default=0.0)
    preco_venda = db.Column(db.Float, nullable=False, default=0.0)
    estoque_minimo = db.Column(db.Integer, nullable=False, default=5)
    estoque_maximo = db.Column(db.Integer, nullable=False, default=100)
    ativo = db.Column(db.Boolean, default=True)

    lotes = db.relationship('Lote', backref='produto', lazy='dynamic')
    movimentacoes = db.relationship('Movimentacao', backref='produto', lazy='dynamic')

    @property
    def estoque_atual(self):
        total = 0
        for lote in self.lotes:
            total += lote.quantidade
        return total

    @property
    def estoque_baixo(self):
        return self.estoque_atual <= self.estoque_minimo

    def calcular_preco_venda(self):
        self.preco_venda = round(self.preco_custo * (1 + self.margem_lucro / 100), 2)

    def __repr__(self):
        return f'<Produto {self.nome}>'


class Lote(db.Model):
    __tablename__ = 'lotes'

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    numero_lote = db.Column(db.String(60))
    quantidade = db.Column(db.Integer, nullable=False, default=0)
    data_validade = db.Column(db.Date)
    data_entrada = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    itens_venda = db.relationship('ItemVenda', backref='lote', lazy='dynamic')
    movimentacoes = db.relationship('Movimentacao', backref='lote', lazy='dynamic')

    @property
    def vencido(self):
        if self.data_validade is None:
            return False
        return self.data_validade < date.today()

    @property
    def proximos_vencimento(self):
        """Retorna True se vence em até 30 dias."""
        if self.data_validade is None:
            return False
        delta = (self.data_validade - date.today()).days
        return 0 <= delta <= 30

    def __repr__(self):
        return f'<Lote {self.id} | Produto {self.produto_id}>'


class Movimentacao(db.Model):
    __tablename__ = 'movimentacoes'

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    lote_id = db.Column(db.Integer, db.ForeignKey('lotes.id'))
    tipo = db.Column(db.String(20), nullable=False)  # 'entrada', 'saida', 'ajuste'
    quantidade = db.Column(db.Integer, nullable=False)
    data = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    motivo = db.Column(db.String(200))

    def __repr__(self):
        return f'<Movimentacao {self.tipo} | {self.quantidade}>'


class Venda(db.Model):
    __tablename__ = 'vendas'

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    total = db.Column(db.Float, nullable=False, default=0.0)

    itens = db.relationship('ItemVenda', backref='venda', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Venda {self.id} | R${self.total:.2f}>'


class ItemVenda(db.Model):
    __tablename__ = 'itens_venda'

    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey('vendas.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    lote_id = db.Column(db.Integer, db.ForeignKey('lotes.id'))
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)

    produto = db.relationship('Produto')

    @property
    def subtotal(self):
        return self.quantidade * self.preco_unitario

    def __repr__(self):
        return f'<ItemVenda venda={self.venda_id} produto={self.produto_id}>'
