# Refurb Laptops - catalog & inquiry app

Django 5.2 LTS · PostgreSQL · Tailwind. No checkout: customers submit an inquiry tied to a laptop.

## Layout

```
config/                 settings, urls, wsgi/asgi
apps/
  core/                 AuditModel (abstract), AuditedModelAdmin, read-only audit-log admin
  accounts/             custom User, roles.py (role -> permissions), `setup_roles` command
  inventory/            Category, Laptop, LaptopImage + admin, selectors, forms, views
  inquiries/            Inquiry model + admin, public submission view (honeypot + rate limit)
templates/              base.html, inventory/{laptop_list,_laptop_card,laptop_detail}.html
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && export $(grep -v '^#' .env | xargs)
createdb laptop_store                 # or via psql
python manage.py migrate              # first migration enables the pg_trgm extension
python manage.py setup_roles          # creates groups: inventory_manager, admin (re-run after adding models)
python manage.py createsuperuser
python manage.py runserver
```

### Creating staff
In `/admin/` > Users, create the user, then tick **Staff status** and add exactly one group
(`inventory_manager` or `admin`). Superusers are treated as administrators too.

## Roles

| | inventory_manager | admin |
|---|---|---|
| Laptops, categories, images | add / change / view | full CRUD |
| Inquiries | view / change (status, notes) | full CRUD |
| Users, audit log | - | yes |
| Delete anything | **never** (no `delete_*` perms + enforced in admin code) | yes |

Every Category / Laptop / LaptopImage stores `created_by`, `created_at`, `updated_by`, `updated_at`.
Admins review work via the "Added by / on" and "Last modified by / on" columns, list filters by person,
the per-object **History** button, and **Admin > Log entries** (all managers' actions, read-only).

## Tests
```bash
DJANGO_DEBUG=1 python manage.py test
```

## Production notes
- Tailwind: base.html uses the Play CDN for development. For production, compile CSS
  (Tailwind standalone CLI: `tailwindcss -i in.css -o static/app.css --minify`, content = `templates/**/*.html`).
- Serve media from object storage / nginx; run behind HTTPS and set `DJANGO_SECRET_KEY`.
- Use a shared cache (Redis) so the inquiry rate limit works across workers.

## Storefront design (electronicsbazaar-inspired)

The public storefront was redesigned to look presentable like electronicsbazaar.com and to support its
refurbished-electronics business model:

- **Top info bar** — support phone (`+91 1800 266 4000`), working hours, admin login.
- **Sticky header** — logo, search bar, **Deals** link, mobile drawer menu.
- **Mega category menu** — Laptops / Desktops & Workstations / Services (ITAD, leasing, bulk buying).
- **Hero banner** — value prop with trust badges: up to 3-year warranty, quality tested, eco-friendly.
- **Product cards** — condition badge, warranty-month badge, stock-aware "Enquire" CTA, discount %.
- **Product detail** — gallery, price + discount, trust badges, primary "Enquire" CTA, full spec sheet.
- **Shop by brand** — brand tiles (HP, Dell, Lenovo, Apple, Acer, Asus, Microsoft) on the homepage.
- **Deals page** — all laptops sorted cheapest first.
- **Footer** — contact info, WhatsApp sales chat, newsletter sign-up, policies, social links.

## Staff dashboard (`/staff/`)

A mobile-first back office for staff (no React build step: Django templates + Tailwind via CDN). It works
on phones, tablets and laptops through one responsive interface:

| URL | What it does |
|-----|--------------|
| `/staff/` | Dashboard: stock counts, new-inquiry count, quick actions |
| `/staff/categories/` | List, add, edit, delete categories |
| `/staff/laptops/` | List, search, filter, add, edit, delete inventory (+ photos) |
| `/staff/inquiries/` | List new inquiries, view detail, update status/owner/notes |

Access is limited to users with `is_staff` (tick **Staff status** in `/admin/` > Users). Permissions match
`apps.accounts.roles`: `inventory_manager` can add/change but never delete; `admin` gets full CRUD.
Every create/update stamps `created_by` / `updated_by` audit fields.

Log in at `/staff/login/`; the storefront header shows an **Admin** link for staff users.

## New models (business model)

- **`Brand`** — manufacturer with logo + slug, powers the brand-browsing section (`/brands/<slug>/`).
- **`NewsletterSubscriber`** — footer newsletter sign-up (`/newsletter/signup/`).
- **`Laptop.warranty_months`** already existed and is now surfaced as a trust badge on cards/detail.

## Path to an API / React / mobile
Read logic lives in `inventory/selectors.py` and write rules in models + `set_audit_user()`, so adding
DRF later means serializers + viewsets that call `selectors.catalog(params)` and
`instance.set_audit_user(request.user)` in `perform_create/perform_update`. No view logic to untangle.
