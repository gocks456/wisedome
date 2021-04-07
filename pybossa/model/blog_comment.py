# -*- coding: utf8 -*-
# This file is part of PYBOSSA.
#
# Copyright (C) 2015 Scifabric LTD.
#
# PYBOSSA is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PYBOSSA is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PYBOSSA.  If not, see <http://www.gnu.org/licenses/>.

from sqlalchemy import Integer, UnicodeText, Text
from sqlalchemy.schema import Column, ForeignKey

from pybossa.core import db
from pybossa.model import DomainObject, make_timestamp
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict


class BlogComment(db.Model, DomainObject):

    __tablename__ = 'blog_comment'

    #: Blog_comment ID
    id = Column(Integer, primary_key=True)
    #: UTC timestamp when the blogpost is created
    created = Column(Text, default=make_timestamp)
    #: UTC timestamp when the blogpost is updated 
    updated = Column(Text, default=make_timestamp)
    #: blog.ID for the comment
    blog_id = Column(Integer, ForeignKey('blogpost.id',
                                            ondelete='CASCADE'),
                        nullable=False)

    #: User.ID for the comment
    # 글쓴이
    user_id = Column(Integer, ForeignKey('user.id'))

    # 내용
    body = Column(UnicodeText, nullable=False)
