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

from pybossa.core import task_repo


blueprint = Blueprint('home', __name__)

import time
@blueprint.route('/')
def home():
    a1 = time.time()
    """Render home page with the cached projects and users."""
    page = 1
    per_page = current_app.config.get('APPS_PER_PAGE', 5)
    print ("1)\t" + str(time.time() - a1))
    a1 = time.time()

    # Add featured
    tmp_projects = cached_projects.get_featured('featured', page, per_page)									# 얘 조금 느림
    print ("2)\t" + str(time.time() - a1))
    a1 = time.time()

    if len(tmp_projects) > 0:
        data = dict(featured=rank(tmp_projects))
    else:
        data = dict(featured=[])
    print ("3)\t" + str(time.time() - a1))
    """
    # Add historical contributions
    historical_projects = []
    if current_user.is_authenticated:
        user_id = current_user.id
        historical_projects = cached_users.projects_contributed(user_id, order_by='last_contribution')[:3]	# 이거 조금 느림
        data['historical_contributions'] = historical_projects
    print ("4)\t" + str(time.time() - a1))
    """
    a1 = time.time()

    # 메인화면 Design Test
    #response = dict(template='/home/index.html', **data)
    #projects = project_repo.get_all()
    projects = cached_projects.get_all_projects()
    print ("5a)\t" + str(time.time() - a1))
    a1 = time.time()
    top_users = site_stats.get_top10_users_7_days()
    print ("5b)\t" + str(time.time() - a1))
    a1 = time.time()
    if current_user.is_anonymous:
        response = dict(template='/new_design/index.html', projects=projects, top_users=top_users )
        print ("6a)\t" + str(time.time() - a1))
        return handle_content_type(response)
    else:
        print ("6b)\t" + str(time.time() - a1))
        return redirect_content_type(url_for('project.index'))


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

@blueprint.route("loadtest")
def lt():
    import sys
    
    print ("@@@")
    a1 = time.time()
    get_all = task_repo.get_all_info()
    print (str(time.time() - a1))
    print ("@@@")
    print (sys.getsizeof(get_all))
    print ("@@@")
    
    print ("###")
    a1 = time.time()
    load_test = cached_projects.loadtest2()
    print (str(time.time() - a1))
    print ("###")
    print (sys.getsizeof(load_test))
    print ("###")
	
    return "AA"


@blueprint.route("loadtest2")
def lt2():
    import sys
    
    print ("@@@")
    a1 = time.time()
    get_all = task_repo.get_all_info2()
    print (str(time.time() - a1))
    print ("@@@")
    print (sys.getsizeof(get_all))
    print ("@@@")
    print (type(get_all[1]))
    
    return "BB"


@blueprint.route("loadtest3")
def lt3():
    import sys
    
    print ("$$$")
    a1 = time.time()
    get_all = task_repo.get_all_info3()
    print (str(time.time() - a1))
    print ("$$$")
    print (sys.getsizeof(get_all))
    print ("$$$")
    print (type(get_all[1]))
    
    return "CC"

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
