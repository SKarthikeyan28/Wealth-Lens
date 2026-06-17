import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.models import User
from backend.crra.elicitation import rational_answers
from backend.crra.models import RiskProfile
from backend.crra.service import get_risk_profile, submit_questionnaire


@pytest.mark.asyncio
async def test_submit_questionnaire_upserts_band_and_point(db_session: AsyncSession) -> None:
    db = db_session
    user_id = uuid.uuid4()
    db.add(User(id=user_id, email=f"risk-{uuid.uuid4().hex}@example.com", password_hash="x"))
    await db.commit()

    # True gamma 2.5 falls in band (2.0, 3.5); midpoint 2.75.
    rp = await submit_questionnaire(db, user_id, rational_answers(2.5))
    assert rp.crra_gamma == Decimal("2.750")
    assert rp.crra_gamma_low == Decimal("2.000")
    assert rp.crra_gamma_high == Decimal("3.500")

    # Round-trip from DB yields the same 3-dp Numeric values.
    fetched = await get_risk_profile(db, user_id)
    assert fetched is not None
    assert fetched.crra_gamma == Decimal("2.750")
    assert fetched.crra_gamma_low == Decimal("2.000")
    assert fetched.crra_gamma_high == Decimal("3.500")

    # Re-submit: true gamma 7.0 -> band (6.0, 10.0), midpoint 8.0. Must UPDATE the
    # same row (unique user constraint), not insert a duplicate.
    rp2 = await submit_questionnaire(db, user_id, rational_answers(7.0))
    assert rp2.crra_gamma == Decimal("8.000")
    assert rp2.crra_gamma_low == Decimal("6.000")
    assert rp2.crra_gamma_high == Decimal("10.000")

    count = await db.scalar(
        select(func.count()).select_from(RiskProfile).where(RiskProfile.user_id == user_id)
    )
    assert count == 1

    again = await get_risk_profile(db, user_id)
    assert again is not None
    assert again.crra_gamma == Decimal("8.000")

    await db.execute(delete(RiskProfile).where(RiskProfile.user_id == user_id))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
