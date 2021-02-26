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

@blueprint.route('/', methods=["GET", "POST"])
def home():
    """Render home page with the cached projects and users."""
    #project_repo.update_end_date_7days()

    if current_user.is_anonymous:
        # 오픈한 모든 프로젝트
        # 개수 지정할 필요있음
        projects = cached_projects.get_projects_limit(8)

        # 7일 간 top 5
        top_users = site_stats.get_top5_users_7_days()
        response = dict(template='/new_design/index2.html', projects=projects, top_users=top_users )
        return handle_content_type(response)
    else: 
        # 오픈된 모든 프로젝트 개수
        n_projects = project_repo.get_count_published_projects().count

        # 참여한 프로젝트 전체
        projects = project_repo.get_contributed_projects_all(current_user.id)

        if request.method == 'POST':
            projects = sort_project(projects, request.form['value'])
            render = render_template('/new_design/workspace/ajax_dashboard.html', projects=projects)
            return render

        # 참여중인 프로젝트 개수
        n_ongoing_projects = len(projects)
        #len(cached_projects.get_ongoing_projects(current_user.id))

        current_point = point_repo.get_current_point(current_user.id)

        response = dict(template='/new_design/workspace/dashboard.html', n_projects=n_projects, n_ongoing_projects=n_ongoing_projects,
                                                               point=current_point, projects=projects
                                                               )
        return handle_content_type(response)
#        return redirect_content_type(url_for('project.index'))


def sort_project(projects, value):
    if value == '최저가격순':
        projects = sorted(projects, key=lambda project: project.all_point)
    elif value == '최고가격순':
        projects = sorted(projects, key=lambda project: project.all_point, reverse=True)
    elif value == '최신순':
        projects = sorted(projects, key=lambda project: project.updated, reverse=True)
    elif value == '마감임박순':
        projects = sorted(projects, key=lambda project: project.end_date, reverse=True)
    return projects



@blueprint.route("qna", defaults={'category':'register'})
@blueprint.route("qna/<category>")
def qna(category):

    board_list = blog_repo.get_category_blogposts(category)
    response = dict(template="new_design/qna/qnaBoard_"+category+".html", board_list=board_list)
    return handle_content_type(response)

@blueprint.route("qna/view/<int:blog_id>", methods=['GET', 'POST'])
def qna_view(blog_id):
    if request.method == "POST":
        from pybossa.model.blog_comment import BlogComment		# 익명은 댓글 못달게 바꾸기
        comment = BlogComment(
                       body=request.form.get('body'),
                       blog_id=blog_id
                       )
        if not current_user.is_anonymous:
            comment.user_id = current_user.id
        blog_repo.save_comment(comment)
        return 'save'
    blog = blog_repo.get(blog_id)
    user = user_repo.get(blog.user_id)
    blog_comment = blog_repo.get_comment(blog_id)
    response = dict(template="new_design/qna/viewQnA.html", blog=blog, user=user, blog_comment=blog_comment, csrf=generate_csrf())
    return handle_content_type(response)
    
@blueprint.route("qna/write/<category>", methods=['GET', 'POST'])
def write(category):
    if request.method == "POST":
        if request.form.get('title') != '' and request.form.get('body') != '<p><br></p>' and request.form.get('subject') != '주제':
            blog = Blogpost(
                        title=request.form.get('title'),
                        body=request.form.get('body'),
                        subject=request.form.get('subject'),
                        category=category
                        )
            if not current_user.is_anonymous:
                blog.user_id = current_user.id
            blog_repo.save(blog)
            return 'success'
        return 'fail'
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
