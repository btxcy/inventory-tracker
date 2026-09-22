# Inventory Tracker

A single-warehouse inventory management system built with Django and Django REST Framework.
Stock levels are backed by an immutable movement ledger, so the number you see and the
history that produced it can never disagree.

## Features

- Product, category and supplier management with a REST API
- Immutable stock movement ledger — every change is recorded, nothing is edited or deleted
- Low-stock endpoint driven by a per-product reorder level
- Soft delete, so historical records never point at a missing product
- Django admin with an add-only ledger and automatic user attribution
- Seed command producing 40 products with a consistent ledger from one command

## Stack

| | |
|---|---|
| Framework | Django 4.2, Django REST Framework 3.16 |
| Database | SQLite in development; designed to move to PostgreSQL unchanged |
| Filtering | django-filter |
| Config | python-dotenv — `SECRET_KEY` and `DEBUG` come from the environment |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then set SECRET_KEY
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo    # 8 categories, 6 suppliers, 40 products
python manage.py runserver
```

Generate a key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

`/api/` lists every endpoint. All endpoints require authentication — log in at
`/api-auth/login/` or `/admin/`.

## API

| Method | Endpoint | Notes |
|---|---|---|
| GET / POST | `/api/products/` | Filter by `category`, `supplier`, `unit`; `?search=` on SKU and name |
| GET / PUT / PATCH / DELETE | `/api/products/{id}/` | `DELETE` is a soft delete |
| GET | `/api/products/low_stock/` | Products at or below their reorder level |
| GET / POST | `/api/movements/` | POST records stock; no `PUT` or `DELETE` exist |
| GET | `/api/movements/{id}/` | Read only |
| GET / POST | `/api/categories/`, `/api/suppliers/` | |

Stock cannot be set directly. `quantity` is read-only on the product serializer, so the
only way to change stock is to record a movement.

## Design decisions

### Stock lives in two places, deliberately

`Product.quantity` holds the current number; `StockMovement` holds every change. This is
the standard ERP pattern — nobody sums an eleven-million-row ledger to render a product
page. The ledger is the source of truth for auditing, the column for operating.

Deriving the quantity from the ledger on every read would never drift, but it makes the
low-stock query impossible to express as a filter, and it breaks pagination: you would
have to load every product into memory before you could page them.

### Concurrency: three active layers, four by design

All stock changes go through `record_movement()`:

| Layer | Prevents | On SQLite |
|---|---|---|
| `transaction.atomic()` | A ledger row written without the matching stock update | Active |
| `F("quantity") - n` | Lost updates when two requests decrement at once | Active |
| `CHECK (quantity >= 0)` | Any path driving stock negative, including raw SQL | Active |
| `select_for_update()` | The gap between the pre-check and the update | **Silently ignored** |

`F()` is what makes the arithmetic safe. It sends `SET quantity = quantity - n` and lets
the database do the subtraction, so there is no read-then-write gap to interleave.
Measured with two concurrent sales of 3 against a stock of 240: 234 with `F()`, 237
without — one sale silently lost.

SQLite does not support row locking and Django drops the clause without raising. Stock
still cannot go negative, because the `CHECK` constraint holds. What degrades is the error
quality: a losing race returns a 500 from `IntegrityError` instead of a 400 from
`InsufficientStock`. The lock activates on PostgreSQL with no code change.

### The ledger stores positive numbers and a type

Never signed quantities. A wrong sign in a permanent record is unfixable in a way an
awkward query never is, so data integrity wins over query elegance. Direction comes from a
single `MOVEMENT_DIRECTION` dict — a `KeyError` on an unclassified type rather than a
silent default. `ADJUSTMENT` is split into `IN` and `OUT` so "always positive" has no
exceptions.

### Money is `Decimal` end to end

`DecimalField` in the model, and explicitly declared `DecimalField(read_only=True)` for the
computed properties — otherwise DRF emits them as floats. Summing 40 products' stock value
gives `2244.65` as `Decimal` and `2244.6499999999996` as `float`.

### Soft delete and `PROTECT`

Products are deactivated, never deleted; hard deletion would orphan every historical sale.
Foreign keys use `PROTECT` so deleting a category cannot silently rewrite hundreds of
product rows. The consequence is real: the cleanup command has to delete children first or
the database refuses.

### A service layer that knows nothing about HTTP

`record_movement()` is called by the API, the admin, the seed command and the shell. It
enforces business rules (enough stock, valid type); the view enforces authorization. The
module imports no DRF — swapping the API framework would not touch it.

### Query performance

`select_related` on the product queryset takes serializing 20 products from 21 queries to
1. The low-stock filter uses `F("reorder_level")` because the threshold differs per row —
there is no single value to compare against, and filtering in Python would load every row
and break pagination.

One composite index exists: `("product", "-created_at")` on the ledger, which serves the
product history page. Two speculative indexes were added and removed — they answered no
real query and only cost writes.

## Tests

```bash
python manage.py test inventory
```

16 tests. The principle is to test the decisions, not the framework. Three of them prove
things that reading the code cannot:

- `test_failed_movement_does_not_save_movement` — a failed movement leaves no ledger row,
  which is the only proof `transaction.atomic()` is working
- `test_database_rejects_negative_quantity` — bypasses the service entirely and expects
  `IntegrityError`, proving the guarantee is in the database, not in Python
- `test_stockmovement_cannot_put` — `PUT` on a movement's detail URL returns 405, proving
  the mixin composition really omits that action

## Known limitations

| | |
|---|---|
| Django 4.2 | LTS support ended April 2026; 5.2 LTS needs Python 3.10+ |
| SQLite | `select_for_update()` is inert until PostgreSQL |
| Error responses | All `StockError` subclasses return `{"detail": "..."}` with no machine-readable code, though the exceptions carry structured data |

## Scoped out deliberately

Real systems track stock per `(product, warehouse)` and separate `on_hand` from
`available`, reserving stock at order time. Both are correct and both would triple the
scope. The cost shows up in a measurable way: with 5 in stock, a sale of 10 and a delivery
of 25 arriving together end at 30 or 20 depending purely on which lands first. That is
correct behaviour — but it is what backorders exist to soften.

## Not built yet

- Dashboard with aggregation endpoints and charts
- `reconcile` command to recompute stock from the ledger and report drift
- Deriving `reorder_level` from `lead_time_days` × average daily demand
- Inventory valuation using the `unit_cost` already recorded on every movement

## How this was built

This project was written in collaboration with Claude (Anthropic) across a series of
working sessions.

**Written by me.** Every model, service, serializer, view, test and frontend script here
was typed by hand. The design decisions documented above — denormalising stock alongside
an immutable ledger, storing movements as positive quantities plus a type, choosing
`PROTECT` over `CASCADE`, composing the movement endpoint from mixins so `PUT` does not
exist rather than being refused — were mine to make and mine to defend.

**Claude's role was review and interrogation.** It read each file as I wrote it and ran
the code to demonstrate failures rather than assert them: a test that passed for the wrong
reason because it asserted on a base exception class, a `select_for_update()` that Django
silently drops on SQLite, a serializer field emitting `21.6` where `"21.60"` was intended,
a `catch` block reporting a successful save as a failure. It pushed back until each
trade-off was explicit, and the limitations section above exists because of that.

**Directly authored by Claude:** `inventory/_seed_data.py` (demo fixtures),
`inventory/pagination.py`, this README, and the local editor configuration. Commits
containing that work carry a `Co-Authored-By` trailer.

A separate design-decision record written up from those sessions covers each choice in
more depth, including the alternatives that were rejected. Available on request.
