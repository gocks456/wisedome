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
from flask import current_app, abort, url_for, request
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
from pybossa.core import project_repo, task_repo, blog_repo, user_repo, point_repo
from pybossa.cache import site_stats
from flask_wtf.csrf import generate_csrf
from pybossa.model.blogpost import Blogpost

blueprint = Blueprint('home', __name__)

import time
@blueprint.route('/')
def home():
    """Render home page with the cached projects and users."""
    page = 1
    per_page = current_app.config.get('APPS_PER_PAGE', 5)

    # Add featured
    tmp_projects = cached_projects.get_featured('featured', page, per_page)									# 얘 조금 느림

    if len(tmp_projects) > 0:
        data = dict(featured=rank(tmp_projects))
    else:
        data = dict(featured=[])
    """
    # Add historical contributions
    historical_projects = []
    if current_user.is_authenticated:
        user_id = current_user.id
        historical_projects = cached_users.projects_contributed(user_id, order_by='last_contribution')[:3]	# 이거 조금 느림
        data['historical_contributions'] = historical_projects
    print ("4)\t" + str(time.time() - a1))
    """

    # 메인화면 Design Test
    #response = dict(template='/home/index.html', **data)
    #projects = project_repo.get_all()

    # 오픈한 모든 프로젝트
	# 개수 지정할 필요있음
    projects = cached_projects.get_all_projects()


    if current_user.is_anonymous:
        # 7일 간 top 5
        top_users = site_stats.get_top5_users_7_days()
        response = dict(template='/new_design/index2.html', projects=projects, top_users=top_users )
        return handle_content_type(response)
    else: 
        # 오픈된 모든 프로젝트 개수
        n_projects = len(projects)

        # 인기 프로젝트
        #popular_projects = cached_projects.get_popular_top5_projects()
        projects = project_repo.get_contributed_projects_all(current_user.id)

        # 참여중인 프로젝트 개수
        n_ongoing_projects = len(projects)
        #len(cached_projects.get_ongoing_projects(current_user.id))

        current_point = point_repo.get_current_point(current_user.id)

        response = dict(template='/new_design/workspace/dashboard.html', n_projects=n_projects, n_ongoing_projects=n_ongoing_projects,
                                                               point=current_point, projects=projects
                                                               )
        return handle_content_type(response)
#        return redirect_content_type(url_for('project.index'))


@blueprint.route("qna", defaults={'category':'회원가입'})
@blueprint.route("qna/<category>")
def qna(category):

    board_list = blog_repo.get_category_blogposts(category)
    response = dict(template="new_design/qna/qnaBoard_"+category+".html", board_list=board_list)
    return handle_content_type(response)

@blueprint.route("qna/view/<int:blog_id>")
def qna_view(blog_id):
    blog = blog_repo.get(blog_id)
    user = user_repo.get(blog.user_id)
    response = dict(template="new_design/qna/viewQnA.html", blog=blog, user=user)
    return handle_content_type(response)
    
@blueprint.route("qna/write/<category>", methods=['GET', 'POST'])
def write(category):
    if request.method == "POST":
        print(request.form.get('body'))
        print(request.form.get('title'))
        print(request.form.get('subject'))
        blog = Blogpost(
                    title=request.form.get('title'),
                    body=request.form.get('body'),
                    subject=request.form.get('subject'),
                    category=category,
                    user_id=current_user.id
                    )
        blog_repo.save(blog)
        return 'success'
    response = dict(template="new_design/qna/editor_"+category+".html", csrf=generate_csrf())
    return handle_content_type(response)

@blueprint.route("faq")
def faq():
    """Render the about template."""
    response = dict(template="/new_design/faq.html")
    return handle_content_type(response)

@blueprint.route("sontest")
def st():
    task_repo.ttest()
    return "KKKK"

@blueprint.route("loadtest")
def lt():
    import sys
    
    print ("@@@")
    a1 = time.time()
    get_all = task_repo.get_all_info2()
    print (str(time.time() - a1))
    print ("@@@")
    print (sys.getsizeof(get_all))
    print ("@@@")
    """
    print ("###")
    a1 = time.time()
    load_test = cached_projects.loadtest2()
    print (str(time.time() - a1))
    print ("###")
    print (sys.getsizeof(load_test))
    print ("###")
    """
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
