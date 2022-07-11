from sqlalchemy import (
    Column,
    BigInteger,
    String,
)
from sqlalchemy.orm import relationship

from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger(), primary_key=True)  # telegram id
    username = Column(String(32), nullable=True)

    expenses = relationship("Expense")
