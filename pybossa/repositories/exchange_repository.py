from sqlalchemy.exc import IntegrityError

from pybossa.repositories import Repository
from pybossa.model.exchange import Exchange
from pybossa.exc import WrongObjectError, DBIntegrityError

class ExchangeRepository(Repository):

	def get(self, id):
		return self.db.session.query(Exchange).get(id)

	def get_exchange(self, user_id):
		return self.db.session.query(Exchange).filter_by(user_id=user_id).one()

	def get_all(self):
		return self.db.session.query(Exchange).all()

	def save(self, exchange):
		self._validate_can_be('saved', exchange)
		try:
			self.db.session.add(exchange)
			self.db.session.commit()
		except IntegrityError as e:
			self.db.session.rollback()
			raise DBIntegrityError(e)

	def update(self, exchange):
		self._validate_can_be('updated', exchange)
		try:
			self.db.session.merge(exchange)
			self.db.session.commit()
		except IntegrityError as e:
			self.db.session.rollback()
			raise DBIntegrityError(e)

	def _validate_can_be(self, action, exchange):
		if not isinstance(exchange, Exchange):
			name = exchange.__class__.__name__
			msg = '%s cannot be %s by %s' % (name, action, self.__class__.__name__)
			raise WrongObjectError(msg)
