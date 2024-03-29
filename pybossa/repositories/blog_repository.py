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

from sqlalchemy.exc import IntegrityError

from pybossa.repositories import Repository
from pybossa.model.blogpost import Blogpost
from pybossa.exc import WrongObjectError, DBIntegrityError

from sqlalchemy import and_


class BlogRepository(Repository):

    def __init__(self, db):
        self.db = db

    def get_comment(self, blog_id):
        from pybossa.model.blog_comment import BlogComment
        from pybossa.model.user import User
        return self.db.session.query(BlogComment.updated, BlogComment.body, User.name, User.admin, User.info).filter(and_(BlogComment.blog_id==blog_id, BlogComment.user_id==User.id)).order_by(BlogComment.updated).all()

    def get_category_blogposts(self, category):
        return self.db.session.query(Blogpost.id, Blogpost.updated, Blogpost.subject, Blogpost.title, Blogpost.answer).filter_by(
                    category=category).order_by(Blogpost.updated.desc()).all()

    def get_lately(self, user_id):
        return self.db.session.query(Blogpost.id).filter_by(user_id=user_id).order_by(Blogpost.created.desc()).first()

    def get_blogposts(self, project_id, owner):
        return self.db.session.query(Blogpost).filter(Blogpost.project_id==project_id, Blogpost.user_id!=owner.id,
                                                      Blogpost.published==True)

    def get(self, id):
        return self.db.session.query(Blogpost).get(id)

    def get_by(self, **attributes):
        return self.db.session.query(Blogpost).filter_by(**attributes).first()

    def filter_by(self, limit=None, offset=0, yielded=False, last_id=None,
                  **filters):
        return self._filter_by(Blogpost, limit, offset, yielded, 
                               last_id, **filters)

    def save(self, blogpost):
        self._validate_can_be('saved', blogpost)
        try:
            self.db.session.add(blogpost)
            self.db.session.commit()
        except IntegrityError as e:
            self.db.session.rollback()
            raise DBIntegrityError(e)

    # 댓글 저장
    def save_comment(self, comment):
        self._validate_can_be_comment('saved', comment)
        try:
            self.db.session.add(comment)
            self.db.session.commit()
        except IntegrityError as e:
            self.db.session.rollback()
            raise DBIntegrityError(e)

    def update(self, blogpost):
        self._validate_can_be('updated', blogpost)
        try:
            self.db.session.merge(blogpost)
            self.db.session.commit()
        except IntegrityError as e:
            self.db.session.rollback()
            raise DBIntegrityError(e)

    def delete(self, blogpost):
        self._validate_can_be('deleted', blogpost)
        blog = self.db.session.query(Blogpost).filter(Blogpost.id==blogpost.id).first()
        self.db.session.delete(blog)
        self.db.session.commit()

    def _validate_can_be(self, action, blogpost):
        if not isinstance(blogpost, Blogpost):
            name = blogpost.__class__.__name__
            msg = '%s cannot be %s by %s' % (name, action, self.__class__.__name__)
            raise WrongObjectError(msg)

    def _validate_can_be_comment(self, action, comment):
        from pybossa.model.blog_comment import BlogComment
        if not isinstance(comment, BlogComment):
            name = blogpost.__class__.__name__
            msg = '%s cannot be %s by %s' % (name, action, self.__class__.__name__)
            raise WrongObjectError(msg)
