import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.accounts.models import Account, AccountType, Holding
from backend.auth.models import User
from backend.cashflow.engine import years_to_fi
from backend.cashflow.models import Expense, Income, IncomeSource
from backend.dashboard.service import allocation, cashflow_summary, net_worth
from backend.market.models import AssetClass, FxRate, Security


@pytest.mark.asyncio
async def test_net_worth_and_allocation_multicurrency(db_session: AsyncSession) -> None:
    db = db_session
    user_id = uuid.uuid4()
    acct_sgd = uuid.uuid4()
    acct_usd = uuid.uuid4()
    sec_id = uuid.uuid4()
    ticker = f"NW{uuid.uuid4().hex[:6].upper()}"

    db.add(User(id=user_id, email=f"nw-{uuid.uuid4().hex}@example.com", password_hash="x"))
    await db.flush()
    db.add(Account(id=acct_sgd, user_id=user_id, name="Cash SGD",
                   account_type=AccountType.CASH, currency="SGD", cash_balance=Decimal("1000.00")))
    db.add(Account(
        id=acct_usd, user_id=user_id, name="Brokerage USD",
        account_type=AccountType.BROKERAGE, currency="USD", cash_balance=Decimal("500.00"),
    ))
    db.add(Security(id=sec_id, ticker=ticker, name="World ETF",
                    asset_class=AssetClass.ETF, exchange="LSE", currency="USD"))
    # USD->SGD = 1.34 as of 2026-03-01
    await db.execute(
        delete(FxRate).where(FxRate.base_currency == "USD", FxRate.quote_currency == "SGD")
    )
    db.add(FxRate(id=uuid.uuid4(), base_currency="USD", quote_currency="SGD",
                  rate=Decimal("1.34"), as_of=date(2026, 3, 1)))
    await db.flush()
    db.add(Holding(id=uuid.uuid4(), account_id=acct_usd, security_id=sec_id,
                   quantity=Decimal("10"), avg_cost=Decimal("100.00")))
    await db.commit()

    on = date(2026, 3, 10)
    # 1000 SGD + (500 USD * 1.34 = 670) + (10*100=1000 USD * 1.34 = 1340) = 3010.00
    assert await net_worth(db, user_id, "SGD", on) == Decimal("3010.00")

    total, slices = await allocation(db, user_id, "SGD", on)
    assert total == Decimal("3010.00")
    by_class = {a: v for a, v, _ in slices}
    assert by_class["CASH"] == Decimal("1670.00")
    assert by_class["ETF"] == Decimal("1340.00")

    await db.execute(delete(Account).where(Account.user_id == user_id))  # cascades holdings
    await db.execute(delete(Security).where(Security.id == sec_id))
    await db.execute(
        delete(FxRate).where(FxRate.base_currency == "USD", FxRate.quote_currency == "SGD")
    )
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()


@pytest.mark.asyncio
async def test_cashflow_summary_trailing_year(db_session: AsyncSession) -> None:
    db = db_session
    user_id = uuid.uuid4()
    db.add(User(id=user_id, email=f"cf-{uuid.uuid4().hex}@example.com", password_hash="x"))
    await db.flush()
    # Three account types prove the three asset queries are distinct:
    #   CASH       -> liquid (runway) AND investable (FI) AND net worth
    #   BROKERAGE  -> investable AND net worth, but NOT liquid
    #   CPF_OA     -> net worth only (locked: NOT liquid, NOT investable)
    db.add(Account(id=uuid.uuid4(), user_id=user_id, name="Cash",
                   account_type=AccountType.CASH, currency="SGD",
                   cash_balance=Decimal("18000.00")))
    db.add(Account(id=uuid.uuid4(), user_id=user_id, name="Brokerage",
                   account_type=AccountType.BROKERAGE, currency="SGD",
                   cash_balance=Decimal("10000.00")))
    db.add(Account(id=uuid.uuid4(), user_id=user_id, name="CPF",
                   account_type=AccountType.CPF_OA, currency="SGD",
                   cash_balance=Decimal("50000.00")))
    # One lump income + expense inside the trailing-12-month window (all SGD -> no FX).
    db.add(Income(id=uuid.uuid4(), user_id=user_id, source_type=IncomeSource.SALARY,
                  amount=Decimal("60000"), currency="SGD", received_on=date(2025, 12, 1)))
    db.add(Expense(id=uuid.uuid4(), user_id=user_id, category="Living",
                   amount=Decimal("36000"), currency="SGD", spent_on=date(2025, 12, 1)))
    await db.commit()

    on = date(2026, 6, 16)
    s = await cashflow_summary(db, user_id, "SGD", on, months=12)

    assert s.savings_rate == Decimal("0.4")          # (60000-36000)/60000
    assert s.monthly_expenses == Decimal("3000")     # 36000 / 12
    assert s.runway_months == Decimal("6")           # liquid 18000 / 3000
    assert s.fi_number == Decimal("900000")          # 36000 / 0.04
    # investable = 18000 CASH + 10000 BROKERAGE = 28000 (CPF excluded); contribution 24000.
    assert s.years_to_fi == years_to_fi(
        Decimal("28000"), Decimal("24000"), Decimal("900000"), Decimal("0.05")
    )

    await db.execute(delete(Income).where(Income.user_id == user_id))
    await db.execute(delete(Expense).where(Expense.user_id == user_id))
    await db.execute(delete(Account).where(Account.user_id == user_id))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()


@pytest.mark.asyncio
async def test_cashflow_summary_fx_and_six_month_window(db_session: AsyncSession) -> None:
    db = db_session
    user_id = uuid.uuid4()
    db.add(User(id=user_id, email=f"cf-{uuid.uuid4().hex}@example.com", password_hash="x"))
    await db.flush()
    db.add(Account(id=uuid.uuid4(), user_id=user_id, name="Cash",
                   account_type=AccountType.CASH, currency="SGD",
                   cash_balance=Decimal("3000.00")))
    # USD income converted at its receipt date: 5000 USD * 1.20 = 6000 SGD.
    await db.execute(
        delete(FxRate).where(FxRate.base_currency == "USD", FxRate.quote_currency == "SGD")
    )
    db.add(FxRate(id=uuid.uuid4(), base_currency="USD", quote_currency="SGD",
                  rate=Decimal("1.20"), as_of=date(2026, 1, 1)))
    db.add(Income(id=uuid.uuid4(), user_id=user_id, source_type=IncomeSource.SALARY,
                  amount=Decimal("5000"), currency="USD", received_on=date(2026, 1, 15)))
    db.add(Expense(id=uuid.uuid4(), user_id=user_id, category="Living",
                   amount=Decimal("3000"), currency="SGD", spent_on=date(2026, 1, 15)))
    await db.commit()

    on = date(2026, 6, 16)
    s = await cashflow_summary(db, user_id, "SGD", on, months=6)

    # window income = 6000 SGD, window expense = 3000 SGD; annualised x (12/6=2).
    assert s.annual_expenses == Decimal("6000")      # 3000 * 2
    assert s.monthly_expenses == Decimal("500")      # 3000 / 6
    assert s.savings_rate == Decimal("0.5")          # (12000-6000)/12000
    assert s.runway_months == Decimal("6")           # liquid 3000 / 500
    assert s.fi_number == Decimal("150000")          # 6000 / 0.04

    await db.execute(delete(Income).where(Income.user_id == user_id))
    await db.execute(delete(Expense).where(Expense.user_id == user_id))
    await db.execute(delete(Account).where(Account.user_id == user_id))
    await db.execute(
        delete(FxRate).where(FxRate.base_currency == "USD", FxRate.quote_currency == "SGD")
    )
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()


@pytest.mark.asyncio
async def test_cashflow_summary_empty_data_is_none(db_session: AsyncSession) -> None:
    db = db_session
    user_id = uuid.uuid4()
    db.add(User(id=user_id, email=f"cf-{uuid.uuid4().hex}@example.com", password_hash="x"))
    await db.flush()
    db.add(Account(id=uuid.uuid4(), user_id=user_id, name="Cash",
                   account_type=AccountType.CASH, currency="SGD",
                   cash_balance=Decimal("5000.00")))
    await db.commit()  # no income, no expenses

    s = await cashflow_summary(db, user_id, "SGD", date(2026, 6, 16))

    assert s.savings_rate is None          # no income
    assert s.runway_months is None         # no expenses -> unbounded
    assert s.fi_number == Decimal("0")     # 0 / 0.04
    assert s.years_to_fi == 0.0            # already at/above a zero target

    await db.execute(delete(Account).where(Account.user_id == user_id))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
