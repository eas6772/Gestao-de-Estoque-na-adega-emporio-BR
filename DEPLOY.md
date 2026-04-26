# Deploy no Render.com

Este guia detalha como fazer o deploy da aplicação Gestão de Estoque no Render.com.

## Pré-requisitos

- Conta no [Render.com](https://render.com)
- Repositório GitHub conectado

## Passo 1: Criar o Banco de Dados PostgreSQL

1. Acesse o painel do Render: https://dashboard.render.com
2. Clique em **"New +"** → **"PostgreSQL"**
3. Preencha:
   - **Name**: `estoque-db` (ou o nome que preferir)
   - **Database**: `estoque` (nome do banco de dados)
   - **User**: `estoque_user` (ou seu usuário preferido)
   - **Region**: Escolha a mais próxima (ex: São Paulo)
   - **PostgreSQL Version**: 15
4. Clique em **"Create Database"**
5. Aguarde a criação (2-3 minutos)
6. Copie a **Internal Database URL** (você precisará dela)

## Passo 2: Criar o Web Service

1. Clique em **"New +"** → **"Web Service"**
2. Selecione seu repositório: `eas6772/Gestao-de-Estoque-na-adega-emporio-BR`
3. Preencha:
   - **Name**: `estoque-app` (ou o nome que preferir)
   - **Environment**: `Python 3`
   - **Region**: Mesma do banco de dados
   - **Branch**: `main`
   - **Build Command**: `cd estoque_app && pip install -r requirements.txt`
   - **Start Command**: Deixe em branco (usará o Procfile)

4. Clique em **"Create Web Service"**

## Passo 3: Configurar Variáveis de Ambiente

No painel do Web Service, vá para **Environment** e adicione:

```
FLASK_ENV=production
SECRET_KEY=seu-chave-secreta-muito-segura-aqui
DATABASE_URL=cole-aqui-a-url-interna-do-postgres
```

### Como gerar um SECRET_KEY seguro:

No terminal (ou na sua máquina local):

```bash
python3 -c "import os; print(os.urandom(32).hex())"
```

Copie o resultado e cole no campo `SECRET_KEY`.

### Onde encontrar a DATABASE_URL:

1. Vá para seu PostgreSQL criado no passo anterior
2. Copie a **Internal Database URL**
3. Cole como valor de `DATABASE_URL`

## Passo 4: Conectar o Banco de Dados

1. Após criar o Web Service, o Render tentará fazer o deploy automaticamente
2. Ele rodar o comando do **release** no Procfile:
   ```
   cd estoque_app && flask --app run.py db upgrade
   ```
3. Isto criará todas as tabelas no PostgreSQL

## Passo 5: Seed (dados iniciais)

Após o deploy bem-sucedido, execute o seed para criar o usuário admin:

**Opção A: Via Render Shell**
1. No painel do Web Service, clique em **"Shell"**
2. Digite:
   ```bash
   cd estoque_app && python seed.py
   ```
3. Pressione Enter

**Opção B: Via terminal local**
```bash
# Certifique-se que tem as variáveis de ambiente localmente
export DATABASE_URL="sua-internal-database-url"
cd estoque_app
python seed.py
```

## Passo 6: Acessar a Aplicação

Após o deploy:

1. Vá para a URL fornecida pelo Render (algo como `https://estoque-app.onrender.com`)
2. Faça login com:
   - **Usuário**: `admin`
   - **Senha**: `123456`

## Troubleshooting

### Erro: "Database connection failed"

- Verifique se a `DATABASE_URL` está correta
- Confirme que usou a **Internal Database URL** (não External)
- Aguarde alguns minutos para o banco ficar pronto

### Erro: "No such module"

- Verifique o **Build Command**: deve estar em `estoque_app/`
- Confirme que `requirements.txt` tem todas as dependências

### Logs

Para ver os logs da aplicação:

1. No painel do Web Service, clique em **"Logs"**
2. Procure por erros e timestamps

## Redeploy Manual

Se precisar fazer redeploy:

1. Vá para o Web Service
2. Clique em **"Manual Deploy"** → **"Deploy latest commit"**

## Próximas Etapas

- Configurar domínio personalizado (se tiver)
- Ativar HTTPS (automático no Render)
- Monitorar logs e performance

---

**Dúvidas?** Verifique o CLAUDE.md para detalhes da arquitetura da aplicação.
