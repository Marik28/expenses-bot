from sqlalchemy.orm import Session


class BaseService:
    def __init__(self, session: Session):
        self.session = session

    def __del__(self):
        self.session.close()

    def _save(self, obj):
        self.session.add(obj)
        self.session.commit()
