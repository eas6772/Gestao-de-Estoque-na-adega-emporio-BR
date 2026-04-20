"""
Popula o banco com dados iniciais: usuário admin e categorias padrão.
Uso: flask --app run.py shell < seed.py
  ou: python seed.py (dentro de estoque_app/)
"""
from app import create_app
from app.extensions import db
from app.models.models import Usuario, Categoria

app = create_app('development')

with app.app_context():
    admin = Usuario.query.filter_by(nome='admin').first()
    if not admin:
        admin = Usuario(nome='admin', perfil='admin')
        admin.set_senha('123456')
        db.session.add(admin)
        print('Usuário admin criado (senha: 123456)')
    else:
        print('Usuário admin já existe.')

    categorias_padrao = ['Bebidas Alcoólicas', 'Bebidas Não Alcoólicas', 'Tabacaria', 'Snacks', 'Outros']
    for nome in categorias_padrao:
        if not Categoria.query.filter_by(nome=nome).first():
            db.session.add(Categoria(nome=nome))
            print(f'Categoria criada: {nome}')

    db.session.commit()
    print('Seed concluído.')
