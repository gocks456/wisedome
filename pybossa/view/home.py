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
"""Home view for PYBOSSA."""
from flask import current_app, abort, url_for
from flask_login import current_user
from pybossa.model.category import Category
from flask import Blueprint
from flask import render_template
from pybossa.cache import projects as cached_projects
from pybossa.cache import users as cached_users
from pybossa.cache import categories as cached_cat
from pybossa.util import rank, handle_content_type, redirect_content_type
from jinja2.exceptions import TemplateNotFound

# New Design
from pybossa.core import project_repo
from pybossa.cache import site_stats


blueprint = Blueprint('home', __name__)


@blueprint.route('/')
def home():
    """Render home page with the cached projects and users."""
    page = 1
    per_page = current_app.config.get('APPS_PER_PAGE', 5)

    # Add featured
    tmp_projects = cached_projects.get_featured('featured', page, per_page)
    if len(tmp_projects) > 0:
        data = dict(featured=rank(tmp_projects))
    else:
        data = dict(featured=[])
    # Add historical contributions
    historical_projects = []
    if current_user.is_authenticated:
        user_id = current_user.id
        historical_projects = cached_users.projects_contributed(user_id, order_by='last_contribution')[:3]
        data['historical_contributions'] = historical_projects

    # 메인화면 Design Test
    #response = dict(template='/home/index.html', **data)
    #projects = project_repo.get_all()

    # 오픈한 모든 프로젝트
    projects = cached_projects.get_all_projects()
    # 7일 간 top 10
    top_users = site_stats.get_top10_users_7_days()


    if current_user.is_anonymous:
        response = dict(template='/new_design/index.html', projects=projects, top_users=top_users )
        return handle_content_type(response)
    else:
        # 인기 프로젝트
        popular_projects = cached_projects.get_popular_top5_projects()

        # 참여중인 프로젝트 개수
        n_ongoing_projects = len(cached_projects.get_ongoing_projects(current_user.id))

        # 오픈한 모든 프로젝트 개수
        n_projects = len(projects)

        response = dict(template='/new_design/dashboard.html', projects=projects, n_projects=n_projects, n_ongoing_projects=n_ongoing_projects,
                                                               popular_projects=popular_projects, feature_projects=tmp_projects)
        return handle_content_type(response)
#        return redirect_content_type(url_for('project.index'))


@blueprint.route("about")
def about():
    """Render the about template."""
    response = dict(template="/home/about.html")
    return handle_content_type(response)

@blueprint.route("faq")
def faq():
    """Render the about template."""
    response = dict(template="/custom/faq.html")
    return handle_content_type(response)

#@blueprint.route("order")
#def requset_order():
#   """Render the about template."""
#   response = dict(template="/order/_order.html")
#   return handle_content_type(response)

@blueprint.route("faq/orderer")
def orderer():
	"""Render the about template."""
	response = dict(template="/custom/faq_orderer.html")
	return handle_content_type(response)

@blueprint.route("faq/worker")
def worker():
	"""Render the about template."""
	response = dict(template="/custom/faq_worker.html")
	return handle_content_type(response)

@blueprint.route("search")
def search():
    """Render search results page."""
    response = dict(template="/home/search.html")
    return handle_content_type(response)

@blueprint.route("results")
def result():
    """Render a results page."""
    try:
        response = dict(template="/home/_results.html")
        return handle_content_type(response)
    except TemplateNotFound:
        return abort(404)
