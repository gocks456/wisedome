from sqlalchemy.exc import IntegrityError

from pybossa.repositories import Repository
from pybossa.model.exchange import Exchange
from pybossa.exc import WrongObjectError, DBIntegrityError
from sqlalchemy import func, and_, desc

class ExchangeRepository(Repository):

	def get_exchange_log(self, user_id):
		from pybossa.model.project import Project
		from pybossa.model.task_run import TaskRun
		from sqlalchemy.sql.expression import null
		q1 = self.db.session.query(Project.name.label('name'), func.sum(TaskRun.point).label('point'), null().label('exchange'),
				func.max(TaskRun.finish_time).label('time')).filter(and_(
					Project.id==TaskRun.project_id, TaskRun.user_id==user_id)).group_by(Project.id, TaskRun.project_id)

		q2 = self.db.session.query(Exchange.exchanged.label('name'), null().label('point'), Exchange.exchange_point.label('exchange'),
				Exchange.finish_time.label('time')).filter(and_(Exchange.user_id==user_id, Exchange.exchanged!=None))
		return q1.union(q2).order_by(desc('time')).all()


	def get_exchanging(self, user_id):
		return self.db.session.query(Exchange).filter(Exchange.exchanged==None).order_by(desc(Exchange.created)).all()


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
