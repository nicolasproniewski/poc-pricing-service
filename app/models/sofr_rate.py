from datetime import date, datetime

from sqlalchemy import Date, DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SofrRate(Base):
    __tablename__ = "sofr_rates"
    __table_args__ = (UniqueConstraint("rate_date", name="uq_sofr_rate_date"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    rate_pct: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
