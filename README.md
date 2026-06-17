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
| `dashboard/` | Net worth, allocation, expense & cash-flow aggregation |
| `montecarlo/` | Goal projection via Monte-Carlo simulation |
| `chatbot/` | LLM Q&A over derived summaries (privacy-by-design) |
| `telegram/` | Telegram bot: add-expense / summary, webhook auth |
| `privacy/` | Account deletion + data export |
| `common/` | Shared DB session, base models, logging, error schemas |

## Security

A deliberate security pass (Phase 5.5). Each control and the threat it addresses:

| Control | Threat addressed |
|---|---|
| Argon2id password hashing (64 MB, t=3) | Offline cracking of leaked hashes; GPU brute-force |
| JWT access + rotating refresh tokens, reuse detection | Session theft, refresh replay |
| TOTP 2FA; secret Fernet-encrypted at rest | Account takeover; secret disclosure on DB leak |
| ORM-parameterised queries only (no raw SQL in app code) | SQL injection |
| Per-IP rate limiting (Redis fixed-window) on auth + expensive endpoints | Brute-force, credential stuffing, cost/DoS amplification |
| Security headers: CSP, HSTS, nosniff, frame-deny, no-referrer | Sniffing, clickjacking, downgrade MITM, referrer leakage |
| CORS locked to known origins; methods/headers narrowed | Cross-origin abuse |
| Append-only audit log on financial mutations | Tamper-evidence; accountability |
| Account deletion: cascade data, preserve pseudonymised audit | Right to erasure vs. record-keeping |
| Data export endpoint (excludes credentials) | Subject-access / portability |
| Webhook auth: constant-time secret-token verification | Forged Telegram updates |
| LLM chatbot sees derived summaries only, never PII | PII leakage to a third-party API |
| Dependency audit (`pip-audit`) + secret scanning (`gitleaks`) | Known-vuln dependencies; committed secrets |

> **Not yet:** CI enforcement of the audit/secret-scan gates (Phase 6.2), and an
> audit retention-purge job (documented retention stance is a follow-up).

## Running locally

```bash
docker compose up
```
