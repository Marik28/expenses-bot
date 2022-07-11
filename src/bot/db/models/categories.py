from sqlalchemy import (
    Column,
    Integer,
    String,
)

from ..database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
