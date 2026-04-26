"""
Inicializa o banco de dados: cria todas as tabelas e popula com dados iniciais.
Roda de forma robusta e idempotente (seguro rodar múltiplas vezes).
"""
import os
import sys

def main():
    try:
        # Setup Flask app com config correta
        from app import create_app
        from app.extensions import db
        from app.models.models import Usuario, Categoria

        env = os.environ.get('FLASK_ENV', 'development')
        config_name = 'production' if env == 'production' else 'development'
        app = create_app(config_name)

        with app.app_context():
            print("=" * 60)
            print("Inicializando banco de dados...")
            print("=" * 60)

            # 1. Criar todas as tabelas
            print("\n[1/3] Criando tabelas...")
            try:
                db.create_all()
                print("✓ Tabelas criadas/verificadas com sucesso")
            except Exception as e:
                print(f"✗ Erro ao criar tabelas: {e}")
                return 1

            # 2. Criar usuário admin se não existir
            print("\n[2/3] Criando usuário admin...")
            try:
                admin = Usuario.query.filter_by(nome='admin').first()
                if not admin:
                    admin = Usuario(nome='admin', perfil='admin')
                    admin.set_senha('123456')
                    db.session.add(admin)
                    db.session.commit()
                    print("✓ Usuário admin criado (senha: 123456)")
                else:
                    print("✓ Usuário admin já existe")
            except Exception as e:
                print(f"✗ Erro ao criar usuário: {e}")
                db.session.rollback()
                return 1

            # 3. Criar categorias padrão se não existirem
            print("\n[3/3] Criando categorias...")
            try:
                categorias_padrao = [
                    'Bebidas Alcoólicas',
                    'Bebidas Não Alcoólicas',
                    'Tabacaria',
                    'Snacks',
                    'Outros'
                ]
                for nome in categorias_padrao:
                    if not Categoria.query.filter_by(nome=nome).first():
                        db.session.add(Categoria(nome=nome))
                db.session.commit()
                print("✓ Categorias criadas/verificadas com sucesso")
            except Exception as e:
                print(f"✗ Erro ao criar categorias: {e}")
                db.session.rollback()
                return 1

            print("\n" + "=" * 60)
            print("✓ Inicialização concluída com sucesso!")
            print("=" * 60)
            return 0

    except Exception as e:
        print(f"\n✗ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
