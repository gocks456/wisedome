from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from pybossa.repositories import Repository
from pybossa.model.achievement import Achievement
from pybossa.exc import WrongObjectError, DBIntegrityError

class AchievementRepository(Repository):

    def get(self, id):
        return self.db.session.query(Achievement).get(id)

    def check_overlap(self, user_id, achieve):
        results = self.db.session.query(Achievement).filter_by(user_id=user_id).all()
        for row in results:
            if row.achievement == achieve:
                return False
        return True

    def save(self, achievement):
        self._validate_can_be('saved', achievement)
        try:
            self.db.session.add(achievement)
            self.db.session.commit()
        except IntegrityError as e:
            self.db.session.rollback()
            raise DBIntegrityError(e)

    def update(self, achievement):
        self._validate_can_be('updated', achievement)
        try:
            self.db.session.merge(achievement)
            self.db.session.commit()
        except IntegrityError as e:
            self.db.session.rollback()
            raise DBIntegrityError(e)

    def _validate_can_be(self, action, achievement):
        if not isinstance(achievement, Achievement):
            name = achievement.__class__.__name__
            msg = '%s cannot be %s by %s' % (name, action, self.__class__.__name__)
            raise WrongObjectError(msg)
