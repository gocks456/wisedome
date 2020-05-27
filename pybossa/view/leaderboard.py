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
"""Leaderboard view for PYBOSSA."""
from flask import Blueprint, current_app, request, abort, redirect
from flask_login import current_user
from pybossa.cache import users as cached_users, categories as cached_cat
from pybossa.util import handle_content_type
from pybossa.core import user_repo, project_repo

blueprint = Blueprint('leaderboard', __name__)


@blueprint.route('/')
@blueprint.route('/window/<int:window>')
def index(window=0):
    """Get the last activity from users and projects."""
    if current_user.is_authenticated:
        user_id = current_user.id
    else:
        user_id = None

    if window >= 10:
        window = 10

    info = request.args.get('info')

    leaderboards = current_app.config.get('LEADERBOARDS')

    if info is not None:
        if leaderboards is None or info not in leaderboards:
            return abort(404)

    top_users = cached_users.get_leaderboard(current_app.config['LEADERBOARD'],
                                             user_id=user_id,
                                             window=window,
                                             info=info)
    one_category = cached_cat.get_one()
    response = dict(template='/stats/index.html',
                    title="Community Leaderboard",
                    category = one_category,
                    top_users=top_users)
    return handle_content_type(response)


@blueprint.route('/category/<string:category>')
def category_index(category):
    if current_user.is_authenticated:
        user_name = user_repo.get(current_user.id).name
    else:
        user_name = None

    rank_category = cached_users.get_category_leaderboard(user_name, category)
    active_cats = project_repo.get_category_by(name=category)
    all_category = cached_cat.get_all()

    response = dict(template='/stats/category_rank.html',
                    title="Category Leaderboard",
                    category_rank = rank_category,
                    categories = all_category,
                    active_cat = active_cats)
    return handle_content_type(response)
