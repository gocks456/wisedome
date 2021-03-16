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

from sqlalchemy import Integer, Unicode, UnicodeText, Text, Boolean
from sqlalchemy.schema import Column, ForeignKey

from pybossa.core import db
from pybossa.model import DomainObject, make_timestamp
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict


class Comment(db.Model, DomainObject):
    """A blog post associated to a given project"""

    __tablename__ = 'comment'

    #: Comment ID
    id = Column(Integer, primary_key=True)
    #: UTC timestamp when the blogpost is created
    created = Column(Text, default=make_timestamp)
    #: UTC timestamp when the blogpost is updated 
    updated = Column(Text, default=make_timestamp)

    #: Blogpost.ID for the Blogpost
    blogpost_id = Column(Integer, ForeignKey('blogpost.id',
                                            ondelete='CASCADE'),
                        nullable=False)

    #: User.ID for the comment
    # 글쓴이
    user_id = Column(Integer, ForeignKey('user.id'))

    #: Body of the comment
    # 내용
    body = Column(UnicodeText, nullable=False)

    #: media_url Heading picture or cover for blogpost
    info = Column(MutableDict.as_mutable(JSONB), default=dict())
    #: Media URL with cover photo for the blog post
    media_url = Column(Text)
    #: Published flag
    # 관리자 및 글 작성자만 보는 글을 작성 시 사용할 예정
    published = Column(Boolean, nullable=False, default=False)


    @classmethod
    def public_attributes(self):
        """Return a list of public attributes."""
        return ['created', 'updated', 'blogpost_id', 'id', 'user_id',
                'body', 'media_url', 'published']

    @classmethod
    def public_info_keys(self):
        """Return a list of public info keys."""
        return []
