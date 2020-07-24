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

from sqlalchemy.sql import text
from pybossa.cache import cache, delete_cached
from pybossa.core import db, timeouts
import pybossa.model as model


session = db.slave_session

@cache(key_prefix="categories_all",
       timeout=timeouts.get('CATEGORY_TIMEOUT'))

def get_list_cat():
    sql = text('''
               SELECT c.*
               FROM category c, project p
               WHERE c.id = p.category_id
               AND p.complete = false
               GROUP BY c.id
               ''')
    results = session.execute(sql,dict())
    list_cat = []
    for row in results:
        cat= dict(id=row.id, name=row.name, short_name=row.short_name, description=row.description, created=row.created, info=row.info)
        list_cat.append(cat)

    return list_cat


def get_all():
    """Return all categories"""
    data = session.query(model.category.Category).all()
    return data

def get_one():
    """Return all categories"""
    data = session.query(model.category.Category).first()
    return data

def get_all_name():
    sql = text('''
               SELECT name AS c_name
               FROM  category
               ''')
    results = session.execute(sql,dict())
    all_category = []
    for row in results:
        name = dict(c_name=row.c_name)
        all_category.append(name)

    return all_category


@cache(key_prefix="categories_used",
       timeout=timeouts.get('CATEGORY_TIMEOUT'))
def get_used():
    """Return categories only used by projects"""
    sql = text('''
               SELECT category.* FROM category, project
               WHERE project.category_id=category.id GROUP BY category.id
               ''')
    results = session.execute(sql)
    categories = []
    for row in results:
        category = dict(id=row.id, name=row.name, short_name=row.short_name,
                        description=row.description)
        categories.append(category)
    return categories


def reset():
    """Clean the cache"""
    delete_cached('categories_all')
    delete_cached('categories_used')
