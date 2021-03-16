from sqlalchemy import Integer, Unicode, Text, Boolean
from sqlalchemy.schema import Column, ForeignKey

from pybossa.core import db
from pybossa.model import DomainObject, make_timestamp



class Exchange(db.Model, DomainObject):

    __tablename__ = 'exchange'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

    request_name = Column(Unicode(length=254), nullable=False)

    bank = Column(Unicode(length=254), nullable=False)

    account_number = Column(Unicode(length=254), nullable=False)

    exchange_point = Column(Integer)

    created = Column(Text, default=make_timestamp)

    finish_time = Column(Text) #, default='F')

    exchanged = Column(Unicode(length=254))

    down_check = Column (Boolean)
