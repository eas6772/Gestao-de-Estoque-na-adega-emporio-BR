# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Gestão de Estoque na Adega — Empório BR** is an inventory management system for a small convenience store (adega) in Santos-SP. Built as an integrative project for UNIVESP (1st semester 2026).

- **Stack**: Python 3 + Flask + SQLAlchemy ORM + SQLite
- **Theme**: Dark mode (green accent `#22c55e`, inspired by financial dashboards)
- **Database**: SQLite (`instance/database.db`)
- **Deployment**: Development server on port 5000 by default

## Development Setup

All development occurs in `estoque_app/` directory.

**Initialize:**
```bash
cd estoque_app
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  (Windows)
pip install -r requirements.txt
```

**Run the application:**
```bash
python run.py
# Server starts at http://localhost:5000
# Login: admin / 123456
```

**Database migrations (after model changes):**
```bash
flask --app run.py db migrate -m "description"
flask --app run.py db upgrade
```

**Initialize seed data (admin user + categories):**
```bash
python seed.py
```

## Architecture

### App Factory Pattern
Entry point: `run.py` → `app/__init__.py:create_app('development')`
- Initializes extensions (db, login_manager, migrate)
- Registers all blueprints
- Creates app context for requests

### Directory Structure
```
estoque_app/
├── app/
│   ├── __init__.py          # App factory
│   ├── extensions.py        # db, login_manager, migrate instances
│   ├── models/
│   │   └── models.py        # SQLAlchemy ORM models
│   ├── routes/
│   │   ├── auth.py          # Login/logout (Blueprint: auth_bp)
│   │   ├── main.py          # Dashboard (Blueprint: main_bp)
│   │   ├── produtos.py      # CRUD products/categories (Blueprint: produtos_bp)
│   │   ├── estoque.py       # Stock management, lots, movements (Blueprint: estoque_bp)
│   │   ├── vendas.py        # PDV (Point of Sale) (Blueprint: vendas_bp)
│   │   └── relatorios.py    # Reports (Blueprint: relatorios_bp)
│   ├── templates/
│   │   ├── base.html        # Main layout (sidebar nav, dark theme)
│   │   ├── auth/, main/, produtos/, estoque/, vendas/, relatorios/
│   └── static/
│       ├── css/styles.css   # Dark theme (CSS variables: --accent, --danger, etc.)
│       └── js/main.js
├── config.py                # Config classes by environment
├── run.py                   # Entry point
├── seed.py                  # Initial data seed
├── requirements.txt
├── instance/                # SQLite DB (git-ignored)
└── migrations/              # Flask-Migrate (auto-generated)
```

### Database Models
All in `app/models/models.py`. Key entities:

- **Usuario**: users with bcrypt-hashed passwords, perfil ('admin'|'operador')
- **Categoria**: product categories
- **Produto**: products with cost/margin logic; `estoque_atual` property sums all lots
- **Lote**: inventory lots with expiry date, batch number (`numero_lote`), quantity
- **Movimentacao**: stock movements (entrada/saida/ajuste) with audit trail
- **Venda**: sales record
- **ItemVenda**: line items of sales, linked to specific lots

**Key property:** `Lote.vencido` blocks expired lots from being sold.

### Routes & Blueprints
Each blueprint registers in `app/__init__.py`. All protected routes use `@login_required`.

| Blueprint | Routes | Purpose |
|-----------|--------|---------|
| auth_bp | `/login`, `/logout` | Session management |
| main_bp | `/` (redirect), `/dashboard` | Dashboard KPIs |
| produtos_bp | `/produtos`, `/produto/*` | Product CRUD (admin only) |
| estoque_bp | `/estoque`, `/estoque/entrada`, `/estoque/movimentacoes` | Stock in/out, lot mgmt |
| vendas_bp | `/venda/nova`, `/venda/<id>/recibo`, `/vendas` | PDV system, receipt, history |
| relatorios_bp | `/relatorios/estoque`, `/relatorios/mais-vendidos`, etc. | 5 analytics reports |

### Key Features by Phase

**Phase 7 — PDV (Point of Sale):**
- Search products by name/barcode/manufacturer (AJAX `buscar-produto`)
- Modal dialog to select specific **lot** being sold
- Client-side cart state (JavaScript array)
- Atomic transaction: Venda + ItemVenda + Movimentacao (all or nothing)
- Lot deduction: `lote.quantidade -= qtd` targets the chosen lot (not PEPS)
- Receipt display with grouped items

**Phase 8 — Reports (just implemented):**
- Estoque Atual: current inventory by product, valued at cost
- Reposição: products below minimum stock, with reorder suggestions
- Mais Vendidos: top 20 products by quantity sold, with revenue %
- Movimentações: full audit log with date/type/operator filters, paginated
- Lucro Bruto: gross profit by product (sale price − cost), margins, totals

### Frontend Conventions

**Dark theme CSS variables** (defined in `styles.css`):
- `--bg-base`, `--bg-surface`, `--bg-card`: layered backgrounds
- `--accent`: #22c55e (green)
- `--danger`, `--warning`, `--info`: status colors
- `--text-primary`, `--text-secondary`, `--text-muted`: text hierarchy

**Class patterns:**
- `.card-dark`: main container with border
- `.section-header`, `.section-title`, `.section-dot`: header styling with colored dot
- `.table-dark-custom`: tables with dark theme
- `.btn-accent`, `.btn-outline`, `.btn-icon`: buttons
- `.empty-state`: centered empty message with icon
- `.status-badge`, `.badge-gray`: inline status indicators
- `.value-ok`, `.value-danger`, `.value-warning`: colored numeric values

**Templates structure:**
- `base.html`: sidebar (fixed left), topbar (fixed top), main content area
- All pages extend `base.html`, override `{% block content %}`
- Flash messages auto-dismiss with Bootstrap 5 alerts

### Validation & Permissions

- **Admin-only CRUD**: product/category creation, inventory adjustments
- **Both roles**: register sales, view reports, enter stock
- **Server-side validation**: expired lots, stock sufficiency, product active status
- **Client-side**: form validation (HTML5), quantity limits (JavaScript)

### Common Tasks

**Add a new report:**
1. Create route in `relatorios_bp` (relatorios.py)
2. Add tab link in `relatorios/_tabs.html`
3. Create template in `templates/relatorios/`
4. Use `@relatorios_bp.route()` decorator with `@login_required`

**Modify a model:**
1. Edit `app/models/models.py`
2. Run `flask --app run.py db migrate` to generate migration
3. Run `flask --app run.py db upgrade` to apply
4. Restart dev server

**Add a new endpoint:**
1. Pick the appropriate blueprint (or create new one)
2. Use `@bp.route()` with methods=['GET', 'POST'] as needed
3. Add `@login_required` for protection
4. Register blueprint in `app/__init__.py` if new

**Test a template change:**
1. Edit HTML in `templates/`
2. Hard-refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
3. Check console for template errors

### Notes for Future Work

- **Phase 9 (Polimento Final)**: CSRF protection (Flask-WTF), pagination everywhere, toast notifications, full flow testing
- CSS is responsive (`@media max-width: 768px` for mobile)
- Database is transactional: use `db.session.rollback()` on errors
- Passwords hashed with Werkzeug; never store plaintext
- All templates use Jinja2 templating engine
- Date/time formatting: use `.strftime()` for display
- Currency formatting: custom Python filter `"%.2f"|format()` → replace "." with ","
- Import paths: always relative to `app/` (e.g., `from app.models.models import Produto`)

### Language & Conventions

- **Code language**: Portuguese (variable names, comments, flash messages)
- **Naming**: snake_case for Python, kebab-case/snake_case for CSS classes
- **Commit messages**: Portuguese, imperative mood (e.g., "Adicionar campo numero_lote")
- **Flash messages**: always in Portuguese, use categories: 'success', 'warning', 'danger', 'info'

