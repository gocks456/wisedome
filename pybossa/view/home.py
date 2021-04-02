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
from flask import current_app, abort, url_for, request, flash
from flask_login import current_user
from flask_babel import gettext
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

@blueprint.route("qna", methods=['GET', 'POST'])
def qna():
    if request.method == "POST":
        board_list = blog_repo.get_category_blogposts(request.form['category'])
        res = dict(template="new_design/qna/ajax_qna_board.html", board_list=board_list)
        return handle_content_type(res)
    board_list = blog_repo.get_category_blogposts('register')
    response = dict(template="new_design/qna/qna_board.html", csrf=generate_csrf(), board_list=board_list)
    return handle_content_type(response)

@blueprint.route("qna/view/<int:blog_id>", methods=['GET', 'POST'])
def qna_view(blog_id):
    if request.method == "POST":
        if current_user.is_anonymous:
            return 'register'
        from pybossa.model.blog_comment import BlogComment
        comment = BlogComment(
                       body=request.form.get('body'),
                       blog_id=blog_id,
                       user_id=current_user.id
                       )
        if current_user.admin:
            blog = blog_repo.get(blog_id)
            blog.answer = True
            blog_repo.update(blog)
        blog_repo.save_comment(comment)
        return 'save'
    blog = blog_repo.get(blog_id)
    blog_comment = blog_repo.get_comment(blog_id)
    if blog.user_id != None:
        user = user_repo.get(blog.user_id)
    else:
        user = None
    response = dict(template="new_design/qna/viewQnA.html", blog=blog, user=user, blog_comment=blog_comment, csrf=generate_csrf())
    if current_user.is_anonymous:
        response = dict(template="new_design/qna/no_login_viewQnA.html", blog=blog, user=user, blog_comment=blog_comment, csrf=generate_csrf())
    return handle_content_type(response)
    
@blueprint.route("qna/write", methods=['GET', 'POST'])
def write():
    if request.method == "POST":
        if request.form.get('title') != '' and request.form.get('body') != '<p><br></p>' and request.form.get('subject') != '주제':
            blog = Blogpost(
                        title=request.form.get('title'),
                        body=request.form.get('body'),
                        subject=request.form.get('subject'),
                        category=request.form.get('category')
                        )
            if not current_user.is_anonymous:
                blog.user_id = current_user.id
            blog_repo.save(blog)
            flash(gettext('게시글 작성 완료'), 'success')
            return url_for('.qna_view', blog_id=blog.id)
        return 'fail'
    response = dict(template="new_design/qna/editor.html", csrf=generate_csrf())
    return handle_content_type(response)

@blueprint.route("qna/rewrite/<int:blog_id>", methods=['GET', 'POST'])
def rewrite(blog_id):
    blog = blog_repo.get(blog_id)
    if current_user.is_anonymous or current_user.id != blog.user_id:
        return abort(403)

    if request.method == "POST":
        if request.form.get('title') != '' and request.form.get('body') != '<p><br></p>' and request.form.get('subject') != '주제':
            blog.title = request.form.get('title')
            blog.body = request.form.get('body')
            blog.subject = request.form.get('subject')
            blog.category = request.form.get('category')
            blog_repo.update(blog)
            flash(gettext('게시글 수정 완료'), 'success')
            return url_for('.qna_view', blog_id=blog.id)
        return 'fail'
    res = dict(template="new_design/qna/re_editor.html", csrf=generate_csrf(), blog=blog, body=blog.body)
    return handle_content_type(res)

@blueprint.route("qna/delete/<int:blog_id>", methods=['POST'])
def delete_blog(blog_id):
    blog = blog_repo.get(blog_id)
    if not current_user.admin:
        if current_user.is_anonymous or current_user.id != blog.user_id:
            return abort(403)

    blog_repo.delete(blog)
    return 'success'

@blueprint.route("faq")
def faq():
    """Render the about template."""
    response = dict(template="/new_design/faq.html")
    return handle_content_type(response)

@blueprint.route("aboutus")
def aboutus():
    response = dict(template="/new_design/aboutus.html")
    return handle_content_type(response)

@blueprint.route("dataBoucher", methods=['GET', 'POST'])
def databoucher():
    if request.method == "POST":
        from pybossa.view.gmail import send_mail, create_message
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        body = render_template('/new_design/email/dataBoucher_email.html', name=name, email=email, message=message)
        msg = create_message(current_app.config['GMAIL'], current_app.config['GMAIL'], "와이즈돔 데이터바우처 문의사항", body)
        send_mail(msg)
        flash(gettext('문의가 접수되었습니다.'), 'success')
    response = dict(template="/new_design/dataBoucher.html", csrf=generate_csrf())
    return handle_content_type(response)
