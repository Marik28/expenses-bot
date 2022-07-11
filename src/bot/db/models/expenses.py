from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    String,
    Date,
    DECIMAL,
    text,
    Boolean,
    BigInteger,
)

from ..database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    date = Column(Date(), nullable=False, server_default=text("now()::date"))
    is_expense = Column(Boolean(), nullable=False)
    amount = Column(DECIMAL(10, 2, asdecimal=True), nullable=False)
    comment = Column(String(255), nullable=True, index=True)
    category_id = Column(Integer(), ForeignKey("categories.id"), nullable=False)
    user_id = Column(BigInteger(), ForeignKey("users.id"), nullable=False)
