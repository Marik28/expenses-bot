from sqlalchemy import (
    Column,
    BigInteger,
    String,
    DECIMAL,
    text,
)
from sqlalchemy.orm import relationship

from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger(), primary_key=True)  # telegram id
    username = Column(String(32), nullable=True)
    balance = Column(DECIMAL(10, 2, asdecimal=True), nullable=False, server_default=text("0.00::numeric"))

    expenses = relationship("Expense")
