from sqlalchemy import Integer, Unicode
from sqlalchemy.schema import Column, ForeignKey

from pybossa.core import db
from pybossa.model import DomainObject



class Point(db.Model, DomainObject):

	__tablename__ = 'point'


	id = Column(Integer, primary_key=True)

	user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), unique=True, nullable=False)

	point_sum = Column(Integer, default=0)

	#exchange = Column(Integer, default=0)

	current_point = Column(Integer, default=0)
