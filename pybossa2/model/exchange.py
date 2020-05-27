from sqlalchemy import Integer, Unicode, Text, Boolean
from sqlalchemy.schema import Column, ForeignKey

from pybossa.core import db
from pybossa.model import DomainObject, make_timestamp



class Exchange(db.Model, DomainObject):

    __tablename__ = 'exchange'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('user.name'), nullable=False)

    request_name = Column(Unicode(length=254), nullable=False)

    bank = Column(Unicode(length=254), nullable=False)

    account_number = Column(Unicode(length=254), nullable=False)

    exchange_point = Column(Integer)

    created = Column(Text) #, default=make_timestamp)

    finish_time = Column(Text) #, default='F')

    exchanged = Column(Unicode(length=2))

#init 기능이 USER에서 대신해줄지 의문
''' 
	def __init__(self, name, task_sum, exchange):
		self.name = name
		self.task_sum = task_sum
		self.exchange = exchange

Base.metadata.create_all(engine)
'''
