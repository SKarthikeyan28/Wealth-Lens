# Wealth-Lens

SG Personal Finance Optimizer — an educational analysis tool for Singaporeans to
understand their net worth, cash flow, and portfolio risk.

> **Disclaimer:** This is an educational/simulation tool only. It does not
> constitute financial advice. No real money is involved.

## Stack

- **Backend:** FastAPI (Python) — modular monolith
- **Frontend:** Next.js (TypeScript)
- **Database:** PostgreSQL 16
- **Cache:** Redis 7
- **Auth:** Argon2id + JWT + TOTP 2FA

## Modules

| Module | Responsibility |
|---|---|
| `auth/` | Registration, login, JWT sessions, 2FA |
| `accounts/` | User accounts (bank, CPF, SRS, brokerage) |
| `ingestion/` | CSV import, idempotent upserts |
| `cashflow/` | Income, expenses, savings rate, runway |
| `market/` | Price history, returns, covariance, FX |
| `crra/` | Risk questionnaire, CRRA gamma, portfolio optimisation |
| `common/` | Shared DB session, base models, logging, error schemas |

## Running locally

```bash
docker compose up
```
