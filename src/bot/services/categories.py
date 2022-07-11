from .base import BaseService
from ..db.models import Category


class CategoriesService(BaseService):

    def add(self, name: str) -> None:
        category = Category()
        category.name = name
        self._save(category)

    def get_list(self) -> list[Category]:
        return self.session.query(Category).order_by(Category.name).all()
