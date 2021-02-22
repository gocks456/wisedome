from sqlalchemy.exc import IntegrityError

from pybossa.repositories import Repository
from pybossa.model.point import Point
from pybossa.model.user import User
from pybossa.exc import WrongObjectError, DBIntegrityError

class PointRepository(Repository):
	def get_current_point(self, user_id):
		return self.db.session.query(Point.current_point).filter_by(user_id=user_id).one()

	def get(self, id):
		return self.db.session.query(Point).get(id)

	def get_point(self, user_id):
		return self.db.session.query(Point).filter_by(user_id=user_id).one()

	def get_all(self):
		return self.db.session.query(Point).all()

	def update_point(self, task_sum, user_id):
		point= self.db.session.query(Point).filter_by(user_id=user_id).one()
		point.point_sum = point.point_sum + task_sum
		#point.current_point = point.point_sum - point.exchange
		self.db.session.commit()


	def exchange(self, user_id, exchange_point):
		point= self.get_point(user_id)
		#point.exchange = point.exchange + exchange_point
		#point.current_point = point.point_sum - point.exchange
		point.current_point = point.current_point - point.exchange
		#user=self.db.session.query(User).get(user_id)
		#user.current_point = point.current_point
		self.db.session.commit()

	def save(self, point):
		self._validate_can_be('saved', point)
		try:
			self.db.session.add(point)
			self.db.session.commit()
		except IntegrityError as e:
			self.db.session.rollback()
			raise DBIntegrityError(e)

	def update(self, point):
		self._validate_can_be('updated', point)
		try:
			self.db.session.merge(point)
			self.db.session.commit()
		except IntegrityError as e:
			self.db.session.rollback()
			raise DBIntegrityError(e)

	def _validate_can_be(self, action, point):
		if not isinstance(point, Point):
			name = point.__class__.__name__
			msg = '%s cannot be %s by %s' % (name, action, self.__class__.__name__)
			raise WrongObjectError(msg)







