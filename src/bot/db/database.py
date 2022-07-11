from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from ..settings import settings

engine = create_engine(settings.db_url)
Session = sessionmaker(bind=engine)
Base = declarative_base()

from .models.categories import Category  # noqa
from .models.users import User  # noqa
from .models.expenses import Expense  # noqa
