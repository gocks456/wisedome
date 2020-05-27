from sqlalchemy import Integer, Unicode
from sqlalchemy.schema import Column, ForeignKey

from pybossa.core import db
from pybossa.model import DomainObject



class Point(db.Model, DomainObject):

	__tablename__ = 'point'


	id = Column(Integer, primary_key=True)

	user_id = Column(Integer, ForeignKey('user.id'), unique=True, nullable=False)

	point_sum = Column(Integer, default=0)

	exchange = Column(Integer, default=0)

	current_point = Column(Integer, default=0)

#init 기능이 USER에서 대신해줄지 의문
''' 
	def __init__(self, name, task_sum, exchange):
		self.name = name
		self.task_sum = task_sum
		self.exchange = exchange

Base.metadata.create_all(engine)
'''
