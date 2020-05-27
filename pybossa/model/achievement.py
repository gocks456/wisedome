from sqlalchemy import Integer, Text
from sqlalchemy.schema import Column, ForeignKey

from pybossa.core import db
from pybossa.model import DomainObject, make_timestamp



class Achievement(db.Model, DomainObject):

    __tablename__ = 'achievement'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)

    created = Column(Text, default=make_timestamp)

    achievement = Column(Text)

    achieve_id = Column(Text, nullable=False)

    category = Column(Text)
