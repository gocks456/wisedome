# -*- coding: utf8 -*-
# This file is part of PYBOSSA.
#
# Copyright (C) 2017 Scifabric LTD.
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

import time
import re
import json
import os
import math
import requests
from io import StringIO, BytesIO
import datetime

from flask import Blueprint, request, url_for, flash, redirect, abort, Response, current_app
from flask import render_template, make_response, session
from flask import Markup
from flask_login import login_required, current_user
from flask_babel import gettext
from flask_wtf.csrf import generate_csrf
from rq import Queue

import pybossa.sched as sched

from pybossa.core import (uploader, signer, sentinel, json_exporter,
                          csv_exporter, importer, sentinel, db, anonymizer)
from pybossa.model import make_uuid
from pybossa.model.project import Project
from pybossa.model.category import Category
from pybossa.model.task import Task
from pybossa.model.task_run import TaskRun
from pybossa.model.auditlog import Auditlog
from pybossa.model.project_stats import ProjectStats
from pybossa.model.webhook import Webhook
from pybossa.model.blogpost import Blogpost
from pybossa.util import (Pagination, admin_required, get_user_id_or_ip, rank,
                          handle_content_type, redirect_content_type,
                          get_avatar_url, fuzzyboolean)
from pybossa.auth import ensure_authorized_to
from pybossa.cache import projects as cached_projects
from pybossa.cache import users as cached_users
from pybossa.cache import categories as cached_cat
from pybossa.cache import project_stats as stats
from pybossa.cache.helpers import add_custom_contrib_button_to, has_no_presenter
from pybossa.ckan import Ckan
from pybossa.extensions import misaka
from pybossa.cookies import CookieHandler
from pybossa.password_manager import ProjectPasswdManager
from pybossa.jobs import import_tasks, webhook
from pybossa.forms.projects_view_forms import *
from pybossa.forms.admin_view_forms import SearchForm
from pybossa.importers import BulkImportException
from pybossa.pro_features import ProFeatureHandler

from pybossa.core import (project_repo, user_repo, task_repo, blog_repo,
                          result_repo, webhook_repo, auditlog_repo, point_repo)
from pybossa.auditlogger import AuditLogger
from pybossa.contributions_guard import ContributionsGuard
from pybossa.default_settings import TIMEOUT
from pybossa.exporter.csv_reports_export import ProjectReportCsvExporter

from pybossa.backup.manage_postgres_db import *
from sqlalchemy.sql import text

blueprint = Blueprint('project', __name__)

MAX_NUM_SYNCHRONOUS_TASKS_IMPORT = 500
auditlogger = AuditLogger(auditlog_repo, caller='web')
importer_queue = Queue('medium',
                       connection=sentinel.master,
                       default_timeout=TIMEOUT)
webhook_queue = Queue('high', connection=sentinel.master)


def sanitize_project_owner(project, owner, current_user, ps=None):
    """Sanitize project and owner data."""
    if current_user.is_authenticated and owner.id == current_user.id:
        if isinstance(project, Project):
            project_sanitized = project.dictize()   # Project object
        else:
            project_sanitized = project             # dict object
        owner_sanitized = cached_users.get_user_summary(owner.name)
    else:   # anonymous or different owner
        if request.headers.get('Content-Type') == 'application/json':
            if isinstance(project, Project):
                project_sanitized = project.to_public_json()            # Project object
            else:
                project_sanitized = Project().to_public_json(project)   # dict object
        else:    # HTML
            # Also dictize for HTML to have same output as authenticated user (see above)
            if isinstance(project, Project):
                project_sanitized = project.dictize()   # Project object
            else:
                project_sanitized = project             # dict object
        owner_sanitized = cached_users.public_get_user_summary(owner.name)
    if ps:
        project_sanitized['n_tasks'] = ps.n_tasks
        project_sanitized['n_task_runs'] = ps.n_tasks
        project_sanitized['n_results'] = ps.n_results
        project_sanitized['n_completed_tasks'] = ps.n_completed_tasks
        project_sanitized['n_volunteers'] = ps.n_volunteers
        project_sanitized['overall_progress'] = ps.overall_progress
        project_sanitized['n_blogposts'] = ps.n_blogposts
        project_sanitized['last_activity'] = ps.last_activity
        project_sanitized['overall_progress'] = ps.overall_progress
    return project_sanitized, owner_sanitized

def zip_enabled(project, user):
    """Return if the user can download a ZIP file."""
    if project.zip_download is False:
        if user.is_anonymous:
            return abort(401)
        if (user.is_authenticated and
            (user.id not in project.owners_ids and
                user.admin is False)):
            return abort(403)


def project_title(project, page_name):
    if not project:  # pragma: no cover
        return "Project not found"
    if page_name is None:
        return "Project: %s" % (project.name)
    return "Project: %s &middot; %s" % (project.name, page_name)


def project_by_shortname(short_name):
    project = project_repo.get_by(short_name=short_name)
    if project:
        # Get owner
        ps = stats.get_stats(project.id, full=True)
        owner = user_repo.get(project.owner_id)
        return (project, owner, ps)
    else:
        return abort(404)


def pro_features(owner=None):
    feature_handler = ProFeatureHandler(current_app.config.get('PRO_FEATURES'))
    pro = {
        'auditlog_enabled': feature_handler.auditlog_enabled_for(current_user),
        'autoimporter_enabled': feature_handler.autoimporter_enabled_for(current_user),
        'webhooks_enabled': feature_handler.webhooks_enabled_for(current_user)
    }
    if owner:
        pro['better_stats_enabled'] = feature_handler.better_stats_enabled_for(
                                          current_user,
                                          owner)
    return pro


# 2020.11.27. 업적 리뉴얼 예정
'''
def achievement_renewal():
    from pybossa.leaderboard import jobs
    print(jobs.update_all_user_answer_rate())
    print(jobs.all_rank_achievement())
    print(jobs.category_rank_achievement())
    return "Success"
'''

@blueprint.route('/category/featured/', defaults={'page': 1}, methods=['GET','POST'])
@blueprint.route('/category/featured/page/<int:page>/')
@login_required
def index(page):
    """List projects in the system"""
    order_by = request.args.get('orderby', None)
    desc = bool(request.args.get('desc', False))

    if request.method == 'POST':
        projects = cached_projects.get_published_projects()
        projects = sort_project(projects, request.form['value'])
        render = render_template('/new_design/workspace/ajax_projectList.html', projects=projects)
        return render

    # New Design
    return project_index(page, cached_projects.get_all_featured,
                          'featured', True, False, order_by, desc)

def user_all_achieve(achieve):
    if current_user.achievement["all"] == "bronze_all":
        achieve[0] = 1
    elif current_user.achievement["all"] == "silver_all":
        achieve[0] = 2
    elif current_user.achievement["all"] == "gold_all":
        achieve[0] = 3
    elif current_user.achievement["all"] == "master_all":
        achieve[0] = 4
    else:
        achieve[0] = 5
    return

def sort_project(projects, value):
    if value == '최저가격순':
        projects = sorted(projects, key=lambda project: project['all_point'])
    elif value == '최고가격순':
        projects = sorted(projects, key=lambda project: project['all_point'], reverse=True)
    elif value == '최신순':
        projects = sorted(projects, key=lambda project: project['updated'], reverse=True)
    elif value == '마감임박순':
        projects = sorted(projects, key=lambda project: project['end_date'], reverse=True)
    return projects

def project_index(page, lookup, category, fallback, use_count, order_by=None,
                  desc=False, pre_ranked=False):
    """Show projects of a category"""
    per_page = current_app.config['APPS_PER_PAGE']
    if category == 'featured':
        projects = cached_projects.get_published_projects()
    else:
        projects = lookup(category)

    count = cached_projects.n_count(category)

    from datetime import datetime

    n_year = datetime.today().year
    # 2020.11.27. 업적 리뉴얼 예정
    #achieve = cached_users.get_category_achieve(current_user.id)
    #user_all_achieve(achieve)

    if category == 'featured':
        #ko_cat = '프리미엄'
        ko_cat = '전체'
    elif category == 'sound':
        ko_cat = '음성'
    elif category == 'image':
        ko_cat = '이미지'
    elif category == 'text':
        ko_cat = '텍스트'
    elif category == 'vidio':
        ko_cat = '비디오'
    else:
        ko_cat = '관리자'

    # 2020.12.04. Login 했을 때 안했을 때 구별 (임시)
    # 2021.02.18. 비로그인시 프로젝트 목록은 메인화면에 구성해준 것 만 확인
    template = '/new_design/workspace/projectList.html'

    template_args = {
        #"achieve": achieve,
        "projects": projects,
        "category": category,
        "ko_cat": ko_cat,
        "template": template,
        "csrf": generate_csrf(),
        "n_year":n_year}

    if use_count:
        template_args.update({"count": count})
    return handle_content_type(template_args)


@blueprint.route('/category/draft/', defaults={'page': 1})
@blueprint.route('/category/draft/page/<int:page>/')
@login_required
@admin_required
def draft(page):
    """Show the Draft projects"""
    order_by = request.args.get('orderby', None)
    desc = bool(request.args.get('desc', False))
    return project_index(page, cached_projects.get_all_draft, 'draft', #XXX
                         False, True, order_by, desc)

@blueprint.route('/category/complete/', defaults={'page': 1})
@blueprint.route('/category/complete/page/<int:page>/')
@login_required
@admin_required
def complete(page):
    """Show the complete projects"""
    order_by = request.args.get('orderby', None)
    desc = bool(request.args.get('desc', False))
    return project_index(page, cached_projects.get_all_complete, 'complete', #XXX
                         False, True, order_by, desc)


@blueprint.route('/category/historical_contributions/', defaults={'page': 1})
@blueprint.route('/category/historical_contributions/page/<int:page>/')
@login_required
def historical_contributions(page):
    """Show the projects a user has previously worked on"""
    order_by = request.args.get('orderby', None)
    desc = bool(request.args.get('desc', False))
    pre_ranked = True
    user_id = current_user.id
    def lookup(*args, **kwargs):
        return cached_users.projects_contributed(user_id, order_by='last_contribution')
    return project_index(page, lookup, 'historical_contributions', False, True, order_by,
                         desc, pre_ranked)

@blueprint.route('/category/<string:category>/', defaults={'page': 1}, methods=['GET','POST'])
@blueprint.route('/category/<string:category>/page/<int:page>/')
def project_cat_index(category=None, page=1):
    """Show Projects that belong to a given category"""
    order_by = request.args.get('orderby', None)
    desc = bool(request.args.get('desc', False))

    if request.method == 'POST':
        projects = cached_projects.get_all(category)
        projects = sort_project(projects, request.form['value'])
        render = render_template('/new_design/workspace/ajax_projectList.html', projects=projects)
        return render
    if category == None:
        return redirect_content_type(url_for('.index'))
    return project_index(page, cached_projects.get_all, category, False, True,
                         order_by, desc)

@blueprint.route('give_point')
@login_required
def give_point():
    #aaaa
    print ("BBBBB")






@blueprint.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    #20.02.28. 수정사항 프로젝트 만드는거 막음
    user = user_repo.get(current_user.id)
    if user.admin != True:
        msg_1 = gettext('관리자가 아닙니다.')
        markup = Markup('<i class="icon-ok"></i> {}')
        flash(markup.format(msg_1), 'warning')
        return redirect_content_type(url_for('home.home'))

    ensure_authorized_to('create', Project)
    form = ProjectForm(request.body)

    def respond(errors):
        response = dict(template='projects/new.html',
                        title=gettext("Create a Project"),
                        form=form, errors=errors)
        return handle_content_type(response)

    def _description_from_long_description():
        if form.description.data:
            return form.description.data
        long_desc = form.long_description.data
        html_long_desc = misaka.render(long_desc)[:-1]
        remove_html_tags_regex = re.compile('<[^>]*>')
        blank_space_regex = re.compile('\n')
        text_desc = remove_html_tags_regex.sub("", html_long_desc)[:255]
        if len(text_desc) >= 252:
            text_desc = text_desc[:-3]
            text_desc += "..."
        description = blank_space_regex.sub(" ", text_desc)
        return description if description else " "

    if request.method != 'POST':
        return respond(False)

    if not form.validate():
        #flash(gettext('Please correct the errors'), 'error')
        flash(gettext('오류를 수정해주세요'), 'error')
        return respond(True)

    info = {}
    category_by_default = cached_cat.get_all()[0]

    n = datetime.datetime.now()
    condition_json = dict()
    condition_json["sex"] = form.option_sex.data
    if form.option_age_start.data =="":
        form.option_age_start.data = 0
    if form.option_age_end.data=="":
        form.option_age_end.data =100
    condition_json["age_s"] = ((n.year) - int(form.option_age_start.data) +1)*10000
    condition_json["age_e"] = ((n.year) - int(form.option_age_end.data) + 2)*10000
    condition_json["all_achieve"] = form.option_all_achieve.data
    condition_json["cat_achieve"] = form.option_cat_achieve.data

    # 마감기한 생성: 생성일 + 7일
    now = datetime.datetime.now()
    end_date = now + datetime.timedelta(days=7).isoformat()

    project = Project(name=form.name.data,
                      short_name=form.short_name.data,
                      description=_description_from_long_description(),
                      long_description=form.long_description.data,
                      owner_id=current_user.id,
                      info=info,

                      #20.02.25. 수정사항
                      all_point=form.all_point.data,
                      #condition=form.condition.data,
                      condition = condition_json,

                      category_id=category_by_default.id,
                      owners_ids=[current_user.id],
                      end_date=end_date)

    project_repo.save(project)

    #msg_1 = gettext('Project created!')
    msg_1 = gettext('프로젝스 생성!')
    flash(Markup('<i class="icon-ok"></i> {}').format(msg_1), 'success')
    markup = Markup('<i class="icon-bullhorn"></i> {} ' +
                    '<strong><a href="https://docs.pybossa.com"> {}' +
                    '</a></strong> {}')
    '''
    flash(markup.format(
              gettext('프로젝트 생성 완료. 프로젝트 세부설정을 해주세요.')),
              #gettext('You can check the '),
              #gettext('Guide and Documentation'),
              #gettext('for adding tasks, a thumbnail, using PYBOSSA.JS, etc.')),
          'success')
    '''
    flash(gettext('프로젝트 생성 완료. 프로젝트 세부설정을 해주세요.'), 'success')
    auditlogger.add_log_entry(None, project, current_user)

    return redirect_content_type(url_for('.update',
                                         short_name=project.short_name))


@blueprint.route('/<short_name>/tasks/taskpresentereditor', methods=['GET', 'POST'])
@login_required
def task_presenter_editor(short_name):
    errors = False
    project, owner, ps = project_by_shortname(short_name)

    title = project_title(project, "Task Presenter Editor")
    ensure_authorized_to('read', project)
    ensure_authorized_to('update', project)

    pro = pro_features()

    form = TaskPresenterForm(request.body)
    form.id.data = project.id
    if request.method == 'POST' and form.validate():
        db_project = project_repo.get(project.id)
        old_project = Project(**db_project.dictize())
        old_info = dict(db_project.info)
        old_info['task_presenter'] = form.editor.data
        db_project.info = old_info
        auditlogger.add_log_entry(old_project, db_project, current_user)
        project_repo.update(db_project)
        #msg_1 = gettext('Task presenter added!')
        msg_1 = gettext('작업 템플릿 추가!')
        markup = Markup('<i class="icon-ok"></i> {}')
        flash(markup.format(msg_1), 'success')
        return redirect_content_type(url_for('.tasks',
                                             short_name=project.short_name))

    # It does not have a validation
    if request.method == 'POST' and not form.validate():  # pragma: no cover
        #flash(gettext('Please correct the errors'), 'error')
        flash(gettext('오류를 수정해주세요'), 'error')
        errors = True

    if project.info.get('task_presenter'):
        form.editor.data = project.info['task_presenter']
    else:
        if not request.args.get('template'):
            #msg_1 = gettext('<strong>Note</strong> You will need to upload the'
            #                ' tasks using the')
            #msg_2 = gettext('CSV importer')
            #msg_3 = gettext(' or download the project bundle and run the'
            #                ' <strong>createTasks.py</strong> script in your'
            #                ' computer')
            msg_1 = gettext('작업 템플릿은 작업에 따라 다르게 추가하여주세요.')
            msg_2 = gettext('작업 추가')
            msg_3 = gettext(' ')
            url = '<a href="%s"> %s</a>' % (url_for('project.import_task',
                                                    short_name=project.short_name), msg_2)
            msg = msg_1 + url + msg_3
            flash(Markup(msg), 'info')

            wrap = lambda i: "projects/presenters/%s.html" % i
            pres_tmpls = list(map(wrap, current_app.config.get('PRESENTERS')))

            project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)
            project_sanitized, owner_sanitized = sanitize_project_owner(project,
                                                                        owner,
                                                                        current_user,
                                                                        ps)
            response = dict(template='projects/task_presenter_options.html',
                            title=title,
                            project=project_sanitized,
                            owner=owner_sanitized,
                            overall_progress=ps.overall_progress,
                            n_tasks=ps.n_tasks,
                            n_task_runs=ps.n_task_runs,
                            last_activity=ps.last_activity,
                            n_completed_tasks=ps.n_completed_tasks,
                            n_volunteers=ps.n_volunteers,
                            presenters=pres_tmpls,
                            pro_features=pro)
            return handle_content_type(response)

        tmpl_uri = "projects/snippets/%s.html" \
            % request.args.get('template')
        tmpl = render_template(tmpl_uri, project=project)
        form.editor.data = tmpl
        #msg = 'Your code will be <em>automagically</em> rendered in \
        #              the <strong>preview section</strong>. Click in the \
        #              preview button!'
        msg = '템플릿 코드는 미리보기를 통해 확인할 수 있습니다.'
        flash(Markup(gettext(msg)), 'info')
    project_sanitized, owner_sanitized = sanitize_project_owner(project,
                                                                owner,
                                                                current_user,
                                                                ps)

    dict_project = add_custom_contrib_button_to(project_sanitized,
                                                get_user_id_or_ip())
    response = dict(template='projects/task_presenter_editor.html',
                    title=title,
                    form=form,
                    project=dict_project,
                    owner=owner_sanitized,
                    overall_progress=ps.overall_progress,
                    n_tasks=ps.n_tasks,
                    n_task_runs=ps.n_task_runs,
                    last_activity=ps.last_activity,
                    n_completed_tasks=ps.n_completed_tasks,
                    n_volunteers=ps.n_volunteers,
                    errors=errors,
                    pro_features=pro)
    return handle_content_type(response)


@blueprint.route('/<short_name>/delete', methods=['GET', 'POST'])
@login_required
def delete(short_name):
    project, owner, ps = project_by_shortname(short_name)

    title = project_title(project, "Delete")
    ensure_authorized_to('read', project)
    ensure_authorized_to('delete', project)

    pro = pro_features()

    project_sanitized, owner_sanitized = sanitize_project_owner(project, owner,
                                                                current_user,
                                                                ps)

    if request.method == 'GET':
        response = dict(template='/projects/delete.html',
                        title=title,
                        project=project_sanitized,
                        owner=owner_sanitized,
                        n_tasks=ps.n_tasks,
                        overall_progress=ps.overall_progress,
                        last_activity=ps.last_activity,
                        pro_features=pro,
                        csrf=generate_csrf())
        return handle_content_type(response)

    if request.body.get('backup') == "backup":
        DB_backup_restore("backup")
    project_repo.delete(project)
    auditlogger.add_log_entry(project, None, current_user)
    #flash(gettext('Project deleted!'), 'success')
    flash(gettext('프로젝트 삭제 완료!'), 'success')
    return redirect_content_type(url_for('account.profile', name=current_user.name))

def condition_form(p_condition):
    n = datetime.datetime.now()
    condition = dict()
    condition["age_s"] = int(n.year - (int(p_condition["age_s"]) / 10000) + 1)
    condition["age_e"] = int(n.year - (int(p_condition["age_e"]) / 10000) + 2)
    if condition["age_s"] == 0:
        condition["age_s"] = ""
    if condition["age_e"] == 100:
        condition["age_e"] = ""
    condition["sex"] = p_condition["sex"]
    condition["all_achieve"] = p_condition["all_achieve"]
    condition["cat_achieve"] = p_condition["cat_achieve"]
    return condition

@blueprint.route('/<short_name>/update', methods=['GET', 'POST'])
@login_required
def update(short_name):
    project, owner, ps = project_by_shortname(short_name)

    def handle_valid_form(form):
        project, owner, ps = project_by_shortname(short_name)

        new_project = project_repo.get_by_shortname(short_name)
        old_project = Project(**new_project.dictize())
        old_info = dict(new_project.info)
        old_project.info = old_info


        n = datetime.datetime.now()
        condition_json = dict()
        condition_json["sex"] = form.option_sex.data
        if form.option_age_start.data =="":
            form.option_age_start.data = 0
        if form.option_age_end.data=="":
            form.option_age_end.data =100
        condition_json["age_s"] = ((n.year) - int(form.option_age_start.data) +1)*10000
        condition_json["age_e"] = ((n.year) - int(form.option_age_end.data) + 2)*10000
        condition_json["all_achieve"] = form.option_all_achieve.data
        condition_json["cat_achieve"] = form.option_cat_achieve.data


        if form.id.data == new_project.id:
            new_project.name = form.name.data
            new_project.short_name = form.short_name.data
            new_project.all_point = form.all_point.data
            new_project.condition = condition_json
            #new_project.complete = form.complete.data
            new_project.description = form.description.data
            new_project.long_description = form.long_description.data
            new_project.webhook = form.webhook.data
            new_project.info = project.info
            new_project.owner_id = project.owner_id
            new_project.allow_anonymous_contributors = fuzzyboolean(form.allow_anonymous_contributors.data)
            new_project.category_id = form.category_id.data
            new_project.zip_download = fuzzyboolean(form.zip_download.data)
            # 마감일
            end_date = datetime.datetime.combine(form.end_date.data, datetime.datetime.min.time()).isoformat()+'.000000'
            new_project.end_date = end_date
            # 채점 방식
            if form.self_score.data == "True":
                self_score = True
            else:
                self_score = False
            new_project.self_score = self_score

        if fuzzyboolean(form.protect.data) and form.password.data:
            new_project.set_password(form.password.data)
        if not fuzzyboolean(form.protect.data):
            new_project.set_password("")

        project_repo.update(new_project)
        auditlogger.add_log_entry(old_project, new_project, current_user)
        cached_cat.reset()
        cached_projects.clean_project(new_project.id)
        #flash(gettext('Project updated!'), 'success')
        flash(gettext('프로젝트 업데이트 완료!'), 'success')
        return redirect_content_type(url_for('.details',
                                     short_name=new_project.short_name))

    ensure_authorized_to('read', project)
    ensure_authorized_to('update', project)

    pro = pro_features()

    title = project_title(project, "Update")
    if request.method == 'GET':
        condition = condition_form(project.condition)
        project.option_sex = condition['sex']
        project.option_age_end = condition['age_e']
        project.option_age_start = condition['age_s']
        project.option_all_achieve = condition['all_achieve']
        project.option_cat_achieve = condition['cat_achieve']
        form = ProjectUpdateForm(obj=project)
        upload_form = AvatarUploadForm()
        categories = project_repo.get_all_categories()
        form.category_id.choices = [(c.id, c.name) for c in categories]
        if project.category_id is None:
            project.category_id = categories[0].id
        form.populate_obj(project)
        form.protect.data = project.needs_password()
        form.end_date = project.end_date
        form.self_score = project.self_score

    if request.method == 'POST':
        upload_form = AvatarUploadForm()
        form = ProjectUpdateForm(request.body)
        categories = cached_cat.get_all()
        form.category_id.choices = [(c.id, c.name) for c in categories]

        if request.form.get('btn') != 'Upload':
            if form.validate():
                return handle_valid_form(form)
            #flash(gettext('Please correct the errors'), 'error')
            flash(gettext('오류를 수정해주세요'), 'error')
        else:
            if upload_form.validate_on_submit():
                project = project_repo.get(project.id)
                _file = request.files['avatar']
                coordinates = (upload_form.x1.data, upload_form.y1.data,
                               upload_form.x2.data, upload_form.y2.data)
                prefix = time.time()
                _file.filename = "project_%s_thumbnail_%i.png" % (project.id, prefix)
                container = "user_%s" % current_user.id

                uploader.upload_file(_file,
                                     container=container,
                                     coordinates=coordinates)
                # Delete previous avatar from storage
                if project.info.get('thumbnail'):
                    uploader.delete_file(project.info['thumbnail'], container)
                project.info['thumbnail'] = _file.filename
                project.info['container'] = container
                upload_method = current_app.config.get('UPLOAD_METHOD')
                thumbnail_url = get_avatar_url(upload_method,
                                               _file.filename,
                                               container,
                                               current_app.config.get('AVATAR_ABSOLUTE')
                                               )
                project.info['thumbnail_url'] = thumbnail_url
                project_repo.save(project)
                #flash(gettext('Your project thumbnail has been updated! It may \
                #                  take some minutes to refresh...'), 'success')
                flash(gettext('프로필사진 업데이트 완료!'), 'success')
            else:
                #flash(gettext('You must provide a file to change the avatar'),
                #      'error')
                flash(gettext('프로필 사진을 추가해주세요'), 'error')
            return redirect_content_type(url_for('.update', short_name=short_name))

    project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)
    project_sanitized, owner_sanitized = sanitize_project_owner(project, owner,
                                                                current_user,
                                                                ps)
    response = dict(template='/projects/update.html',
                    form=form,
                    upload_form=upload_form,
                    project=project_sanitized,
                    owner=owner_sanitized,
                    n_tasks=ps.n_tasks,
                    overall_progress=ps.overall_progress,
                    n_task_runs=ps.n_task_runs,
                    last_activity=ps.last_activity,
                    n_completed_tasks=ps.n_completed_tasks,
                    n_volunteers=ps.n_volunteers,
                    title=title,
                    pro_features=pro)
    return handle_content_type(response)


@blueprint.route('/<short_name>/', methods=['GET', 'POST'])
@login_required
def details(short_name):
    project, owner, ps = project_by_shortname(short_name)

    if request.method == 'POST':
        user = user_repo.get(current_user.id)
        if request.form['value'] == 'dislike':
            user.like_projects.append(project.id)
            user_repo.update(user)
            return 'like'
        elif request.form['value'] == 'like':
            user.like_projects.remove(project.id)
            user_repo.update(user)
            return 'dislike'

    if project.needs_password():
        redirect_to_password = _check_if_redirect_to_password(project)
        if redirect_to_password:
            return redirect_to_password
    else:
        ensure_authorized_to('read', project)

    #template = '/projects/project.html'
    template = 'new_design/workspace/projectDescription.html'
    pro = pro_features()

    gender = project.condition["sex"]
    min_a = project.condition["age_s"]
    max_a = project.condition["age_e"]
    from datetime import datetime

    n_year = datetime.today().year

    title = project_title(project, None)
    project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)
    project_sanitized, owner_sanitized = sanitize_project_owner(project, owner,
                                                                current_user,
                                                                ps)
    like_project = 'dislike'
    if current_user.like_projects != None:
        for like_pro_id in current_user.like_projects:
            if like_pro_id == project['id']:
                like_project = 'like'

    template_args = {"project": project_sanitized,
                     "title": title,
                     "owner":  owner_sanitized,
                     "n_tasks": ps.n_tasks,
                     "n_task_runs": ps.n_task_runs,
                     "overall_progress": ps.overall_progress,
                     "last_activity": ps.last_activity,
                     "n_completed_tasks": ps.n_completed_tasks,
                     "n_volunteers": ps.n_volunteers,
                     "pro_features": pro,
                     "like_project": like_project,
                     "gender" : gender,
                     "min": min_a,
                     "max": max_a,
                     "n_year" : n_year,
                     "csrf": generate_csrf()}
    if current_app.config.get('CKAN_URL'):
        template_args['ckan_name'] = current_app.config.get('CKAN_NAME')
        template_args['ckan_url'] = current_app.config.get('CKAN_URL')
        template_args['ckan_pkg_name'] = short_name
    response = dict(template=template, **template_args)
    return handle_content_type(response)


@blueprint.route('/<short_name>/settings')
@login_required
def settings(short_name):
    project, owner, ps = project_by_shortname(short_name)

    title = project_title(project, "Settings")
    ensure_authorized_to('read', project)
    ensure_authorized_to('update', project)
    pro = pro_features()
    project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)
    owner_serialized = cached_users.get_user_summary(owner.name)
    response = dict(template='/projects/settings.html',
                    project=project,
                    owner=owner_serialized,
                    n_tasks=ps.n_tasks,
                    overall_progress=ps.overall_progress,
                    n_task_runs=ps.n_task_runs,
                    last_activity=ps.last_activity,
                    n_completed_tasks=ps.n_completed_tasks,
                    n_volunteers=ps.n_volunteers,
                    title=title,
                    pro_features=pro)
    return handle_content_type(response)


@blueprint.route('/<short_name>/tasks/import', methods=['GET', 'POST'])
@login_required
def import_task(short_name):
    project, owner, ps = project_by_shortname(short_name)

    ensure_authorized_to('read', project)
    ensure_authorized_to('update', project)

    title = project_title(project, "Import Tasks")
    loading_text = gettext("Importing tasks, this may take a while, wait...")
    pro = pro_features()
    dict_project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)
    project_sanitized, owner_sanitized = sanitize_project_owner(dict_project,
                                                                owner,
                                                                current_user,
                                                                ps)
    template_args = dict(title=title, loading_text=loading_text,
                         project=project_sanitized,
                         owner=owner_sanitized,
                         n_tasks=ps.n_tasks,
                         overall_progress=ps.overall_progress,
                         n_volunteers=ps.n_volunteers,
                         n_completed_tasks=ps.n_completed_tasks,
                         target='project.import_task',
                         pro_features=pro)

    importer_type = request.form.get('form_name') or request.args.get('type')
    all_importers = importer.get_all_importer_names()
    if importer_type is not None and importer_type not in all_importers:
        return abort(404)
    form = GenericBulkTaskImportForm()(importer_type, request.body)
    template_args['form'] = form

    if request.method == 'POST':
        if form.validate():  # pragma: no cover
            try:
                return _import_tasks(project, **form.get_import_data())
            except BulkImportException as err_msg:
                raise
                flash(err_msg, 'error')
            except Exception as inst:  # pragma: no cover
                raise
                current_app.logger.error(inst)
                #msg = 'Oops! Looks like there was an error!'
                msg = '오류 발생'
                flash(gettext(msg), 'error')
        template_args['template'] = '/projects/importers/%s.html' % importer_type
        return handle_content_type(template_args)

    if request.method == 'GET':
        template_tasks = current_app.config.get('TEMPLATE_TASKS')
        if importer_type is None:
            template_wrap = lambda i: "projects/tasks/gdocs-%s.html" % i
            task_tmpls = list(map(template_wrap, template_tasks))
            template_args['task_tmpls'] = task_tmpls
            importer_wrap = lambda i: "projects/tasks/%s.html" % i
            template_args['available_importers'] = list(map(importer_wrap, all_importers))
            template_args['template'] = '/projects/task_import_options.html'
            return handle_content_type(template_args)
        if importer_type == 'gdocs' and request.args.get('template'):  # pragma: no cover
            template = request.args.get('template')
            form.googledocs_url.data = template_tasks.get(template)
        template_args['template'] = '/projects/importers/%s.html' % importer_type
        return handle_content_type(template_args)


def _import_tasks(project, **form_data):
    number_of_tasks = importer.count_tasks_to_import(**form_data)
    if number_of_tasks <= MAX_NUM_SYNCHRONOUS_TASKS_IMPORT:
        report = importer.create_tasks(task_repo, project.id, **form_data)
        flash(report.message)
    else:
        importer_queue.enqueue(import_tasks, project.id, **form_data)
        flash(gettext("You're trying to import a large amount of tasks, so please be patient.\
            You will receive an email when the tasks are ready."))
    return redirect_content_type(url_for('.tasks',
                                         short_name=project.short_name))


@blueprint.route('/<short_name>/tasks/autoimporter', methods=['GET', 'POST'])
@login_required
def setup_autoimporter(short_name):
    pro = pro_features()
    if not pro['autoimporter_enabled']:
        raise abort(403)

    project, owner, ps = project_by_shortname(short_name)

    dict_project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)
    template_args = dict(project=dict_project,
                         owner=owner,
                         n_tasks=ps.n_tasks,
                         overall_progress=ps.overall_progress,
                         n_volunteers=ps.n_volunteers,
                         n_completed_tasks=ps.n_completed_tasks,
                         pro_features=pro,
                         target='project.setup_autoimporter')
    ensure_authorized_to('read', project)
    ensure_authorized_to('update', project)
    importer_type = request.form.get('form_name') or request.args.get('type')
    all_importers = importer.get_autoimporter_names()
    if importer_type is not None and importer_type not in all_importers:
        raise abort(404)
    form = GenericBulkTaskImportForm()(importer_type, request.form)
    template_args['form'] = form

    if project.has_autoimporter():
        current_autoimporter = project.get_autoimporter()
        importer_info = dict(**current_autoimporter)
        return render_template('/projects/task_autoimporter.html',
                                importer=importer_info, **template_args)

    if request.method == 'POST':
        if form.validate():  # pragma: no cover
            project.set_autoimporter(form.get_import_data())
            project_repo.save(project)
            auditlogger.log_event(project, current_user, 'create', 'autoimporter',
                                  'Nothing', json.dumps(project.get_autoimporter()))
            #flash(gettext("Success! Tasks will be imported daily."))
            flash(gettext("완료! 매일 작업이 추가될 것입니다."))
            return redirect(url_for('.setup_autoimporter', short_name=project.short_name))

    if request.method == 'GET':
        if importer_type is None:
            wrap = lambda i: "projects/tasks/%s.html" % i
            template_args['available_importers'] = list(map(wrap, all_importers))
            return render_template('projects/task_autoimport_options.html',
                                   **template_args)
    return render_template('/projects/importers/%s.html' % importer_type,
                                **template_args)


@blueprint.route('/<short_name>/tasks/autoimporter/delete', methods=['POST'])
@login_required
def delete_autoimporter(short_name):
    pro = pro_features()
    if not pro['autoimporter_enabled']:
        raise abort(403)

    project = project_by_shortname(short_name)[0]

    ensure_authorized_to('read', project)
    ensure_authorized_to('update', project)
    if project.has_autoimporter():
        autoimporter = project.get_autoimporter()
        project.delete_autoimporter()
        project_repo.save(project)
        auditlogger.log_event(project, current_user, 'delete', 'autoimporter',
                              json.dumps(autoimporter), 'Nothing')
    return redirect(url_for('.tasks', short_name=project.short_name))


@blueprint.route('/<short_name>/password', methods=['GET', 'POST'])
def password_required(short_name):
    project, owner, ps = project_by_shortname(short_name)
    form = PasswordForm(request.form)
    if request.method == 'POST' and form.validate():
        password = request.form.get('password')
        cookie_exp = current_app.config.get('PASSWD_COOKIE_TIMEOUT')
        passwd_mngr = ProjectPasswdManager(CookieHandler(request, signer, cookie_exp))
        if passwd_mngr.validates(password, project):
            response = make_response(redirect(request.args.get('next')))
            return passwd_mngr.update_response(response, project, get_user_id_or_ip())
        #flash(gettext('Sorry, incorrect password'))
        flash(gettext('비밀번호가 일치하지 않습니다.'))
    return render_template('projects/password.html',
                            project=project,
                            form=form,
                            short_name=short_name,
                            next=request.args.get('next'))


@blueprint.route('/<short_name>/task/<int:task_id>', methods=['GET','POST'])
@login_required
def task_presenter(short_name, task_id):
    project, owner, ps = project_by_shortname(short_name)
    task_run = task_repo.get_task_run_present(project.id, current_user.id, task_id)

    if request.method == "POST":
        if request.form.get('btn', None) == "Upload" :
            _file = request.files['fileInput']
            if _file.content_type != 'image/png' and _file.content_type != 'image/jpg' and _file.content_type != 'image/jpeg':
                flash(gettext("jpg 또는 png 파일만 업로드 가능합니다."), "error")
                return redirect_content_type(url_for('.task_presenter', short_name=project.short_name, task_id=task_id))
            _file.seek(0, os.SEEK_END)
            size = _file.tell()
            if size == 0:
                flash(gettext("저장할 파일이 존재하지 않습니다."), "error")
                return redirect_content_type(url_for('.task_presenter', short_name=project.short_name, task_id=task_id))
            _file.seek(0)
            prefix = time.time()
            _file.filename = "%i.png" % (prefix)

            container = "projects/%s/user_id_%i" % (short_name, current_user.id)
            uploader.delete_img(container)
            if not uploader.dir_size(container):
                flash(gettext("업로드 제한 초과"), "error")
                return redirect_content_type(url_for('.task_presenter', short_name=project.short_name, task_id=task_id))
            from tempfile import SpooledTemporaryFile
            stream = _file.stream
            print(stream)
            print(stream.__dict__)
            print(stream._file)
            uploader.upload_file(_file,
                                 container=container)
            flash(gettext("저장 완료!"), "success")
            return redirect_content_type(url_for('.presenter', short_name=project.short_name))


        def get_task_run_by_rank(rank):
            session = db.slave_session
            sql = text('''SELECT * FROM
                          (SELECT task_run.id AS id, task.info AS task_info, task_run.info AS task_run_info,
                          DENSE_RANK() OVER(ORDER BY task_run.created) rank
                          FROM task, task_run
                          WHERE task_run.task_id = task.id
                          AND task_run.user_id=:user_id
                          AND task_run.project_id=:project_id
                          ORDER BY task_run.finish_time) AS t_run
                          WHERE rank =:rank;
                          ''')
            temp = session.execute(sql, dict(user_id=current_user.id, project_id=project.id, rank=rank))
            results = []
            for row in temp:
                result = dict(id=row.id, task_info=row.task_info, task_run_info=row.task_run_info)
                results.append(result)
            return results


        # 프로젝트 진행 중 답변 관리를 눌렀을 때 (답변관리의 value로 바꿔주어야 함)
        if request.form.get('btn', None) == "answer_manager":
            count = task_repo.count_task_runs_with(project_id=project.id, user_id=current_user.id)
            task_run = get_task_run_by_rank(count)
            
            res=dict(count=count, task_run=task_run)
            return json.dumps(res, ensure_ascii=False)

        # 답변 관리에서 원하는 답변을 리턴
        if request.form.get('btn', None) == "get_answer_data":
            result = get_task_run_by_rank(request.form['id'])
            return json.dumps(result, ensure_ascii=False)

        # 답변 관리 후 수정 단계
        if request.form.get('btn', None) == "modify":
            task_run = task_repo.get_task_run(int(request.form["task_run_id"]))
            old_answer = task_run.info
            task_run.info = request.form["answer"]
            task_repo.update(task_run)

            # 답변 수정 후 포인트 업데이트
            task_repo.task_update_point(project.id, task_run.task_id)

            return old_answer

        # 경쟁 관계
        if request.form.get('value', None) == "ranking":
            my_count = task_repo.count_task_runs_with(project_id=project.id, user_id=current_user.id)
            people_count = task_repo.count_task_runs_with(project_id=project.id)

            res = dict(my_count=my_count, people_count=people_count//len(project.contractor_ids))
            return json.dumps(res, ensure_ascii=False)

    task = task_repo.get_task(id=task_id)
    if task is None:
        raise abort(404)
    if project.needs_password():
        redirect_to_password = _check_if_redirect_to_password(project)
        if redirect_to_password:
            return redirect_to_password
    else:
        ensure_authorized_to('read', project)

    if current_user.is_anonymous:
        if not project.allow_anonymous_contributors:
            #msg = ("Oops! You have to sign in to participate in "
            #       "<strong>%s</strong>"
            #       "project" % project.name)
            msg = ("프로젝트 참여를 원하신다면 로그인해주세요.")
            flash(Markup(gettext(msg)), 'warning')
            return redirect(url_for('account.signin',
                                    next=url_for('.presenter',
                                    short_name=project.short_name)))
        else:
            #msg_1 = gettext(
            #    "Ooops! You are an anonymous user and will not "
            #    "get any credit"
            #    " for your contributions.")
            msg_1 = gettext("익명의 사용자는 포인트를 얻을 수 없습니다.")
            #msg_2 = gettext('Sign in now!')
            msg_2 = gettext('로그인 해주세요!')
            next_url = url_for('project.task_presenter',
                                short_name=short_name, task_id=task_id)
            url = url_for('account.signin', next=next_url)
            markup = Markup('{{}} <a href="{}">{{}}</a>'.format(url))
            flash(markup.format(msg_1, msg_2), "warning")

    title = project_title(project, "Contribute")
    project_sanitized, owner_sanitized = sanitize_project_owner(project, owner,
                                                                current_user,
                                                                ps)
    #long_desc_ex = project.long_description.split('## 예시')[1].split('## 이용방법 보기')[0]
    #long_desc_htd = project.long_description.split('## 이용방법 보기')[1]




    template_args = {"project": project_sanitized, "title": title, "owner": owner_sanitized, #"ex" : long_desc_ex, "htd" : long_desc_htd,
                     "task_run": task_run, "n_tasks":ps.n_tasks, "csrf": generate_csrf()}

    def respond(tmpl):
        response = dict(template = tmpl, **template_args)
        return handle_content_type(response)

    if not (task.project_id == project.id):
        return respond('/projects/task/wrong.html')

    guard = ContributionsGuard(sentinel.master)
    guard.stamp(task, get_user_id_or_ip())

    if has_no_presenter(project):
        #flash(gettext("Sorry, but this project is still a draft and does "
        #              "not have a task presenter."), "error")
        flash(gettext("죄송합니다, 이 프로젝트는 임시 프로젝트입니다."), "error")
    #return respond('/projects/presenter.html')
    return respond('/new_design/workspace/presenter.html')


@blueprint.route('/<short_name>/presenter')
@blueprint.route('/<short_name>/newtask', methods=['GET','POST'])
@login_required
def presenter(short_name):

    def invite_new_volunteers(project, ps):
        user_id = None if current_user.is_anonymous else current_user.id
        user_ip = (anonymizer.ip(request.remote_addr or '127.0.0.1')
                   if current_user.is_anonymous else None)
        task = sched.new_task(project.id,
                              project.info.get('sched'),
                              user_id, user_ip, 0)
        return task == [] and ps.overall_progress < 100.0

    def respond(tmpl):
        if (current_user.is_anonymous):
            msg_1 = gettext(msg)
            flash(msg_1, "warning")
        resp = make_response(render_template(tmpl, **template_args))
        return resp

    project, owner, ps = project_by_shortname(short_name)

    if project.needs_password():
        redirect_to_password = _check_if_redirect_to_password(project)
        if redirect_to_password:
            return redirect_to_password
    else:
        ensure_authorized_to('read', project)

    title = project_title(project, "Contribute")
    template_args = {"project": project, "title": title, "owner": owner, "current_user": current_user, "n_tasks": ps.n_tasks,
              "invite_new_volunteers": invite_new_volunteers(project, ps), "task_run":None, "csrf":generate_csrf()}

    if not project.allow_anonymous_contributors and current_user.is_anonymous:
        #msg = "Oops! You have to sign in to participate in <strong>%s</strong> \
        #       project" % project.name
        msg = "프로젝트 참여를 원하신다면 로그인 해주세요"
        flash(Markup(gettext(msg)), 'warning')
        return redirect(url_for('account.signin',
                        next=url_for('.presenter',
                                     short_name=project.short_name)))

    #msg = "Ooops! You are an anonymous user and will not \
    #       get any credit for your contributions. Sign in \
    #       now!"
    msg = "익명의 사용자는 포인트를 얻을 수 없습니다."

    def Contract_upload():
        import base64
        from werkzeug.datastructures import FileStorage
        from tempfile import SpooledTemporaryFile
        
        contract = base64.b64decode(request.form['contract'][22:]) # base64 -> Image

        _file = FileStorage() # FileStorage 생성

        stream = SpooledTemporaryFile() # 이미지를 저장할 임시 파일 생성
        stream._max_size = 512000
        stream.write(contract) # 임시 파일에 이미지 데이터 저장

        # FileStorage에 값 추가
        _file.stream = stream
        _file.name = 'contract'
        _file.filename = current_user.email_addr + ".png"
        _file.headers = "Headers([('Content-Disposition', 'form-data; name='contract'; filename='temp.png''), ('Content-Type', 'image/png')])"
        _file.seek(0, os.SEEK_END)
        _file.seek(0)

        # 저장할 경로 지정 및 File 저장
        container = "project_%s/contract" % (project.name)
        uploader.upload_file(_file, container=container)
        flash(gettext("계약서 작성 완료!"), "success")
        return

    if request.method == "POST" and request.form['contract']:
        if request.form["user_id"] in project.contractor_ids:
            return respond('/projects/presenter.html')
        Contract_upload()
        project.contractor_ids.append(int(request.form['user_id']))
        project_repo.update(project)
        return "success"

    #2020.09.22. 계약서 연결
    if current_user.id not in project.contractor_ids and current_user.id not in project.owners_ids and current_user.admin:
        resp = respond('/projects/tutorial.html')
        return resp

    #if project.info.get("tutorial") and \
    #        request.cookies.get(project.short_name + "tutorial") is None:
    #    resp = respond('/projects/tutorial.html')
    #    resp.set_cookie(project.short_name + 'tutorial', 'seen')
    #    return resp
    else:
        if has_no_presenter(project):
            #flash(gettext("Sorry, but this project is still a draft and does "
            #              "not have a task presenter."), "error")
            flash(gettext("죄송합니다, 이 프로젝트는 임시 프로젝트입니다."), "error")
        return respond('/new_design/workspace/presenter.html')

@blueprint.route('/<short_name>/sertification', methods=['GET','POST'])
def sertification(short_name):
    if request.method == "POST" and request.form['passwd']:
        user = user_repo.get(request.form['user_id'])
        password = request.form['passwd']
        if user.check_password(password):
            return "success"
        return "fail"

    project, owner, ps = project_by_shortname(short_name)

    if current_user.id not in project.contractor_ids and project.info['tutorial'] != "":
        response = dict(template='/projects/sertification.html', current_user=current_user,
                        csrf=generate_csrf())
        return handle_content_type(response)
    elif current_user.id not in project.contractor_ids:
        project.contractor_ids.append(current_user.id)
        project_repo.update(project)
    return redirect_content_type(url_for('.presenter', short_name=project.short_name))

@blueprint.route('/<short_name>/tutorial')
def tutorial(short_name):
    project, owner, ps = project_by_shortname(short_name)
    title = project_title(project, "Tutorial")

    if project.needs_password():
        redirect_to_password = _check_if_redirect_to_password(project)
        if redirect_to_password:
            return redirect_to_password
    else:
        ensure_authorized_to('read', project)

    project_sanitized, owner_sanitized = sanitize_project_owner(project, owner,
                                                                current_user,
                                                                ps)

    response = dict(template='/projects/tutorial.html', title=title,
                    project=project_sanitized, owner=owner_sanitized)

    return handle_content_type(response)


@blueprint.route('/<short_name>/<int:task_id>/results.json')
def export(short_name, task_id):
    """Return a file with all the TaskRuns for a given Task"""
    # Check if the project exists
    project, owner, ps = project_by_shortname(short_name)

    if project.needs_password():
        redirect_to_password = _check_if_redirect_to_password(project)
        if redirect_to_password:
            return redirect_to_password
    else:
        ensure_authorized_to('read', project)

    # Check if the task belongs to the project and exists
    task = task_repo.get_task_by(project_id=project.id, id=task_id)
    if task:
        taskruns = task_repo.filter_task_runs_by(task_id=task_id, project_id=project.id)
        results = [tr.dictize() for tr in taskruns]
        return Response(json.dumps(results), mimetype='application/json')
    else:
        return abort(404)

@blueprint.route('/<short_name>/<int:task_id>/score2')
def score2(short_name, task_id):
    """Return a file with all the TaskRuns for a given Task"""
    # Check if the project exists
    project, owner, ps = project_by_shortname(short_name)

    if project.needs_password():
        redirect_to_password = _check_if_redirect_to_password(project)
        if redirect_to_password:
            return redirect_to_password
    else:
        ensure_authorized_to('read', project)

    # Check if the task belongs to the project and exists
    task = task_repo.get_task_by(project_id=project.id, id=task_id)
    if task:
        taskruns = task_repo.filter_task_runs_by(task_id=task_id, project_id=project.id)
        results = [tr.dictize() for tr in taskruns]
        task1 = dict(id=task.id, info = task.info)
        response = dict(template = '/projects/score2.html', t_r = results, project = project, task=task1)
        return handle_content_type(response)
    else:
        print ("@@@")
        return abort(404)

@blueprint.route('/<short_name>/tasks/', methods=['GET','POST'])
@login_required
def tasks(short_name):

    project, owner, ps = project_by_shortname(short_name)
    title = project_title(project, "Tasks")

    if project.needs_password():
        redirect_to_password = _check_if_redirect_to_password(project)
        if redirect_to_password:
            return redirect_to_password
    else:
        ensure_authorized_to('read', project)

    pro = pro_features()
    project = add_custom_contrib_button_to(project, get_user_id_or_ip())
    feature_handler = ProFeatureHandler(current_app.config.get('PRO_FEATURES'))
    autoimporter_enabled = feature_handler.autoimporter_enabled_for(current_user)

    project_sanitized, owner_sanitized = sanitize_project_owner(project,
                                                                owner,
                                                                current_user,
                                                                ps)

    response = dict(template='/projects/tasks.html',
                    title=title,
                    project=project_sanitized,
                    owner=owner_sanitized,
                    autoimporter_enabled=autoimporter_enabled,
                    n_tasks=ps.n_tasks,
                    n_task_runs=ps.n_task_runs,
                    overall_progress=ps.overall_progress,
                    last_activity=ps.last_activity,
                    n_completed_tasks=ps.n_completed_tasks,
                    n_volunteers=ps.n_volunteers,
                    pro_features=pro)

    return handle_content_type(response)



@blueprint.route('/<short_name>/tasks/givepoint')
@blueprint.route('/<short_name>/tasks/givepoint/<int:page>')
def give_points(short_name, page=1):
    project, owner, ps = project_by_shortname(short_name)
    title = project_title(project, "Tasks")
    pro = pro_features()

    def respond():
        per_page = 10
        offset = (page - 1) * per_page
        count = ps.n_tasks
        page_tasks = cached_projects.browse_tasks(project.get('id'), per_page, offset)
        if not page_tasks and page != 1:
            abort(404)

        pagination = Pagination(page, per_page, count)

        project_sanitized, owner_sanitized = sanitize_project_owner(project,
                                                                    owner,
                                                                    current_user,
                                                                    ps)
        print (project_sanitized)

        data = dict(template='/projects/give_point.html',
                    project=project_sanitized,
                    owner=owner_sanitized,
                    tasks=page_tasks,
                    title=title,
                    pagination=pagination,
                    n_tasks=ps.n_tasks,
                    overall_progress=ps.overall_progress,
                    n_volunteers=ps.n_volunteers,
                    n_completed_tasks=ps.n_completed_tasks,
                    pro_features=pro)

        return handle_content_type(data)

    if project.needs_password():
        redirect_to_password = _check_if_redirect_to_password(project)
        if redirect_to_password:
            return redirect_to_password
    else:
        ensure_authorized_to('read', project)

    zip_enabled(project, current_user)

    project = add_custom_contrib_button_to(project, get_user_id_or_ip())
    return respond()




@blueprint.route('/<short_name>/tasks/browse')
@blueprint.route('/<short_name>/tasks/browse/<int:page>')
def tasks_browse(short_name, page=1):
    project, owner, ps = project_by_shortname(short_name)
    title = project_title(project, "Tasks")
    pro = pro_features()

    def respond():
        per_page = 10
        offset = (page - 1) * per_page
        count = ps.n_tasks
        page_tasks = cached_projects.browse_tasks(project.get('id'), per_page, offset)
        if not page_tasks and page != 1:
            abort(404)

        pagination = Pagination(page, per_page, count)

        project_sanitized, owner_sanitized = sanitize_project_owner(project,
                                                                    owner,
                                                                    current_user,
                                                                    ps)

        data = dict(template='/projects/tasks_browse.html',
                    project=project_sanitized,
                    owner=owner_sanitized,
                    tasks=page_tasks,
                    title=title,
                    pagination=pagination,
                    n_tasks=ps.n_tasks,
                    overall_progress=ps.overall_progress,
                    n_volunteers=ps.n_volunteers,
                    n_completed_tasks=ps.n_completed_tasks,
                    pro_features=pro)

        return handle_content_type(data)

    if project.needs_password():
        redirect_to_password = _check_if_redirect_to_password(project)
        if redirect_to_password:
            return redirect_to_password
    else:
        ensure_authorized_to('read', project)

    zip_enabled(project, current_user)

    project = add_custom_contrib_button_to(project, get_user_id_or_ip())
    return respond()


@blueprint.route('/<short_name>/tasks/delete', methods=['GET', 'POST'])
@login_required
def delete_tasks(short_name):
    """Delete ALL the tasks for a given project"""
    project, owner, ps = project_by_shortname(short_name)
    ensure_authorized_to('read', project)
    ensure_authorized_to('update', project)
    pro = pro_features()
    if request.method == 'GET':
        title = project_title(project, "Delete")
        n_volunteers = cached_projects.n_volunteers(project.id)
        n_completed_tasks = cached_projects.n_completed_tasks(project.id)
        project = add_custom_contrib_button_to(project, get_user_id_or_ip())
        project_sanitized, owner_sanitized = sanitize_project_owner(project,
                                                                    owner,
                                                                    current_user,
                                                                    ps)
        response = dict(template='projects/tasks/delete.html',
                        project=project_sanitized,
                        owner=owner_sanitized,
                        n_tasks=ps.n_tasks,
                        n_task_runs=ps.n_task_runs,
                        n_volunteers=ps.n_volunteers,
                        n_completed_tasks=ps.n_completed_tasks,
                        overall_progress=ps.overall_progress,
                        last_activity=ps.last_activity,
                        title=title,
                        pro_features=pro,
                        csrf=generate_csrf())
        return handle_content_type(response)
    else:
        task_repo.delete_valid_from_project(project)
        #msg = gettext("Tasks and taskruns with no associated results have been deleted")
        msg = gettext("작업과 답변을 모두 삭제하였습니다.")
        flash(msg, 'success')
        return redirect_content_type(url_for('.tasks', short_name=project.short_name))


@blueprint.route('/<short_name>/tasks/export')
def export_to(short_name):
    """Export Tasks and TaskRuns in the given format"""
    project, owner, ps = project_by_shortname(short_name)
    supported_tables = ['task', 'task_run', 'result', 'QnA']

    title = project_title(project, gettext("Export"))

    loading_text = gettext("Exporting data..., this may take a while")

    pro = pro_features()

    if project.needs_password():
        redirect_to_password = _check_if_redirect_to_password(project)
        if redirect_to_password:
            return redirect_to_password
    else:
        ensure_authorized_to('read', project)

    zip_enabled(project, current_user)

    def respond():
        return render_template('/projects/export.html',
                               title=title,
                               loading_text=loading_text,
                               ckan_name=current_app.config.get('CKAN_NAME'),
                               project=project,
                               owner=owner,
                               n_tasks=ps.n_tasks,
                               n_task_runs=ps.n_task_runs,
                               n_volunteers=ps.n_volunteers,
                               n_completed_tasks=ps.n_completed_tasks,
                               overall_progress=ps.overall_progress,
                               pro_features=pro)

    def respond_json(ty):
        if ty not in supported_tables:
            return abort(404)
        res = json_exporter.response_zip(project, ty)
        return res

    def respond_csv(ty):
        if ty not in supported_tables:
            return abort(404)
        res = csv_exporter.response_zip(project, ty)
        return res

    def create_ckan_datastore(ckan, table, package_id, records):
        new_resource = ckan.resource_create(name=table,
                                            package_id=package_id)
        ckan.datastore_create(name=table,
                              resource_id=new_resource['result']['id'])
        ckan.datastore_upsert(name=table,
                              records=records,
                              resource_id=new_resource['result']['id'])

    def respond_ckan(ty):
        # First check if there is a package (dataset) in CKAN
        msg_1 = gettext("Data exported to ")
        msg = msg_1 + "%s ..." % current_app.config['CKAN_URL']
        ckan = Ckan(url=current_app.config['CKAN_URL'],
                    api_key=current_user.ckan_api)
        project_url = url_for('.details', short_name=project.short_name, _external=True)

        try:
            package, e = ckan.package_exists(name=project.short_name)
            records = json_exporter.gen_json(ty, project.id)
            if e:
                raise e
            if package:
                # Update the package
                owner = user_repo.get(project.owner_id)
                package = ckan.package_update(project=project, user=owner,
                                              url=project_url,
                                              resources=package['resources'])

                ckan.package = package
                resource_found = False
                for r in package['resources']:
                    if r['name'] == ty:
                        ckan.datastore_delete(name=ty, resource_id=r['id'])
                        ckan.datastore_create(name=ty, resource_id=r['id'])
                        ckan.datastore_upsert(name=ty,
                                              records=records,
                                              resource_id=r['id'])
                        resource_found = True
                        break
                if not resource_found:
                    create_ckan_datastore(ckan, ty, package['id'], records)
            else:
                owner = user_repo.get(project.owner_id)
                package = ckan.package_create(project=project, user=owner,
                                              url=project_url)
                create_ckan_datastore(ckan, ty, package['id'], records)
            flash(msg, 'success')
            return respond()
        except requests.exceptions.ConnectionError:
            msg = "CKAN server seems to be down, try again layer or contact the CKAN admins"
            current_app.logger.error(msg)
            flash(msg, 'danger')
        except Exception as inst:
            if len(inst.args) == 3:
                t, msg, status_code = inst.args
                msg = ("Error: %s with status code: %s" % (t, status_code))
            else:  # pragma: no cover
                msg = ("Error: %s" % inst.args[0])
            current_app.logger.error(msg)
            flash(msg, 'danger')
        finally:
            return respond()

    export_formats = ["json", "csv"]
    if current_user.is_authenticated:
        if current_user.ckan_api:
            export_formats.append('ckan')

    ty = request.args.get('type')
    fmt = request.args.get('format')
    if not (fmt and ty):
        if len(request.args) >= 1:
            abort(404)
        project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)
        return respond()

    if fmt not in export_formats:
        abort(415)

    if ty == 'task':
        task = task_repo.get_task_by(project_id=project.id)
        if task:
            ensure_authorized_to('read', task)
    if ty == 'task_run':
        task_run = task_repo.get_task_run_by(project_id=project.id)
        if task_run:
            ensure_authorized_to('read', task_run)

    if ty == 'QnA':
        task = task_repo.get_task_by(project_id=project.id)
        if task:
            ensure_authorized_to('read', task)
        task_run = task_repo.get_task_run_by(project_id=project.id)
        if task_run:
            ensure_authorized_to('read', task_run)

    return {"json": respond_json, "csv": respond_csv,
            'ckan': respond_ckan}[fmt](ty)


@blueprint.route('/<short_name>/stats')
def show_stats(short_name):
    """Returns Project Stats"""
    project, owner, ps = project_by_shortname(short_name)
    title = project_title(project, "Statistics")
    pro = pro_features(owner)

    if project.needs_password():
        redirect_to_password = _check_if_redirect_to_password(project)
        if redirect_to_password:
            return redirect_to_password
    else:
        ensure_authorized_to('read', project)

    project_sanitized, owner_sanitized = sanitize_project_owner(project,
                                                                owner,
                                                                current_user,
                                                                ps)
    #sonst = cached_projects.get_redundancy(short_name)
    #print (sonst)

    if not ((ps.n_tasks > 0) and (ps.n_task_runs > 0)):
        project = add_custom_contrib_button_to(project, get_user_id_or_ip(),
                                               ps=ps)
        response = dict(template='/projects/non_stats.html',
                        title=title,
                        project=project_sanitized,
                        owner=owner_sanitized,
                        n_tasks=ps.n_tasks,
                        overall_progress=ps.overall_progress,
                        n_volunteers=ps.n_volunteers,
                        n_completed_tasks=ps.n_completed_tasks,
                        pro_features=pro)
        return handle_content_type(response)

    #백그라운드가 잘 작동할 시 안해도됨
    stats.update_stats(project.id)

    project_task = task_repo.get_task_by(project_id=project.id)
    progress_rate = round((ps.n_task_runs / (ps.n_tasks * project_task.n_answers) * 100), 2)

    dates_stats = ps.info['dates_stats']
    hours_stats = ps.info['hours_stats']
    users_stats = ps.info['users_stats']

    total_contribs = (users_stats['n_anon'] + users_stats['n_auth'])
    if total_contribs > 0:
        anon_pct_taskruns = int((users_stats['n_anon'] * 100) / total_contribs)
        auth_pct_taskruns = 100 - anon_pct_taskruns
    else:
        anon_pct_taskruns = 0
        auth_pct_taskruns = 0

    userStats = dict(
        anonymous=dict(
            users=users_stats['n_anon'],
            taskruns=users_stats['n_anon'],
            pct_taskruns=anon_pct_taskruns,
            top5=users_stats['anon']['top5']),
        authenticated=dict(
            users=users_stats['n_auth'],
            taskruns=users_stats['n_auth'],
            pct_taskruns=auth_pct_taskruns,
            top5=users_stats['auth']['top5']))

    projectStats = dict(
        userStats=users_stats['users'],
        userAnonStats=users_stats['anon'],
        userAuthStats=users_stats['auth'],
        dayStats=dates_stats,
        hourStats=hours_stats)

    project_dict = add_custom_contrib_button_to(project, get_user_id_or_ip(),
                                                ps=ps)
    formatted_contrib_time = round(ps.average_time, 2)

    project_sanitized, owner_sanitized = sanitize_project_owner(project, owner,
                                                                current_user,
                                                                ps)

    # Handle JSON project stats depending of output
    # (needs to be escaped for HTML)
    if request.headers.get('Content-Type') == 'application/json':
        handle_projectStats = projectStats
    else:   # HTML
        handle_projectStats = json.dumps(projectStats)

    response = dict(template='/projects/stats.html',
    #response = dict(template='/projects/orderer_stats.html',
                    title=title,
                    progress_rate=progress_rate,
                    projectStats=handle_projectStats,
                    userStats=userStats,
                    project=project_sanitized,
                    owner=owner_sanitized,
                    n_tasks=ps.n_tasks,
                    overall_progress=ps.overall_progress,
                    n_volunteers=ps.n_volunteers,
                    n_completed_tasks=ps.n_completed_tasks,
                    avg_contrib_time=formatted_contrib_time,
                    pro_features=pro)

    return handle_content_type(response)


@blueprint.route('/<short_name>/tasks/settings')
@login_required
def task_settings(short_name):
    """Settings page for tasks of the project"""
    project, owner, ps = project_by_shortname(short_name)

    ensure_authorized_to('read', project)
    ensure_authorized_to('update', project)
    pro = pro_features()
    project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)
    return render_template('projects/task_settings.html',
                           project=project,
                           owner=owner,
                           n_tasks=ps.n_tasks,
                           overall_progress=ps.overall_progress,
                           n_volunteers=ps.n_volunteers,
                           n_completed_tasks=ps.n_completed_tasks,
                           pro_features=pro)


@blueprint.route('/<short_name>/tasks/redundancy', methods=['GET', 'POST'])
@login_required
def task_n_answers(short_name):
    project, owner, ps = project_by_shortname(short_name)

    title = project_title(project, gettext('Redundancy'))
    form = TaskRedundancyForm(request.body)
    ensure_authorized_to('read', project)
    ensure_authorized_to('update', project)
    pro = pro_features()
    project_sanitized, owner_sanitized = sanitize_project_owner(project,
                                                                owner,
                                                                current_user,
                                                                ps)
    if request.method == 'GET':
        response = dict(template='/projects/task_n_answers.html',
                        title=title,
                        form=form,
                        project=project_sanitized,
                        owner=owner_sanitized,
                        pro_features=pro)
        return handle_content_type(response)
    elif request.method == 'POST' and form.validate():
        task_repo.update_tasks_redundancy(project, form.n_answers.data)
        # Log it
        auditlogger.log_event(project, current_user, 'update', 'task.n_answers',
                              'N/A', form.n_answers.data)
        #msg = gettext('Redundancy of Tasks updated!')
        msg = gettext('반복 수 업데이트 완료!')
        flash(msg, 'success')
        return redirect_content_type(url_for('.tasks', short_name=project.short_name))
    else:
        #flash(gettext('Please correct the errors'), 'error')
        flash(gettext('오류를 수정해주세요'), 'error')
        response = dict(template='/projects/task_n_answers.html',
                        title=title,
                        form=form,
                        project=project_sanitized,
                        owner=owner_sanitized,
                        pro_features=pro)
        return handle_content_type(response)


@blueprint.route('/<short_name>/tasks/scheduler', methods=['GET', 'POST'])
@login_required
def task_scheduler(short_name):
    project, owner, ps = project_by_shortname(short_name)

    title = project_title(project, gettext('Task Scheduler'))
    form = TaskSchedulerForm(request.body)
    pro = pro_features()


    def respond():
        project_sanitized, owner_sanitized = sanitize_project_owner(project,
                                                                    owner,
                                                                    current_user,
                                                                    ps)
        response = dict(template='/projects/task_scheduler.html',
                        title=title,
                        form=form,
                        project=project_sanitized,
                        owner=owner_sanitized,
                        pro_features=pro)
        return handle_content_type(response)

    ensure_authorized_to('read', project)
    ensure_authorized_to('update', project)

    if request.method == 'GET':
        if project.info.get('sched'):
            for s in form.sched.choices:
                if project.info['sched'] == s[0]:
                    form.sched.data = s[0]
                    break
        return respond()

    if request.method == 'POST' and form.validate():
        project = project_repo.get_by_shortname(short_name=project.short_name)
        if project.info.get('sched'):
            old_sched = project.info['sched']
        else:
            old_sched = 'default'
        if form.sched.data:
            project.info['sched'] = form.sched.data
        project_repo.save(project)
        # Log it
        if old_sched != project.info['sched']:
            auditlogger.log_event(project, current_user, 'update', 'sched',
                                  old_sched, project.info['sched'])
        #msg = gettext("Project Task Scheduler updated!")
        msg = gettext("스케쥴러 업데이트 완료!")
        flash(msg, 'success')

        return redirect_content_type(url_for('.tasks', short_name=project.short_name))
    else:  # pragma: no cover
        #flash(gettext('Please correct the errors'), 'error')
        flash(gettext('오류를 수정해주세요'), 'error')
        return respond()


@blueprint.route('/<short_name>/tasks/priority', methods=['GET', 'POST'])
@login_required
def task_priority(short_name):
    project, owner, ps = project_by_shortname(short_name)

    title = project_title(project, gettext('Task Priority'))
    form = TaskPriorityForm(request.body)
    pro = pro_features()

    def respond():
        project_sanitized, owner_sanitized = sanitize_project_owner(project,
                                                                    owner,
                                                                    current_user,
                                                                    ps)
        response = dict(template='/projects/task_priority.html',
                        title=title,
                        form=form,
                        project=project_sanitized,
                        owner=owner_sanitized,
                        pro_features=pro)
        return handle_content_type(response)
    ensure_authorized_to('read', project)
    ensure_authorized_to('update', project)

    if request.method == 'GET':
        return respond()
    if request.method == 'POST' and form.validate():
        for task_id in form.task_ids.data.split(","):
            if task_id != '':
                t = task_repo.get_task_by(project_id=project.id, id=int(task_id))
                if t:
                    old_priority = t.priority_0
                    t.priority_0 = form.priority_0.data
                    task_repo.update(t)

                    if old_priority != t.priority_0:
                        old_value = json.dumps({'task_id': t.id,
                                                'task_priority_0': old_priority})
                        new_value = json.dumps({'task_id': t.id,
                                                'task_priority_0': t.priority_0})
                        auditlogger.log_event(project, current_user, 'update',
                                              'task.priority_0',
                                              old_value, new_value)
                else:  # pragma: no cover
                    #flash(gettext(("Ooops, Task.id=%s does not belong to the project" % task_id)), 'danger')
                    flash(gettext(("%s 는 존재하지 않습니다" % task_id)), 'danger')
        #flash(gettext("Task priority has been changed"), 'success')
        flash(gettext("우선순위 변경 완료"), 'success')
        return respond()
    else:
        #flash(gettext('Please correct the errors'), 'error')
        flash(gettext('오류를 수정해주세요'), 'error')
        return respond()


@blueprint.route('/<short_name>/blog')
def show_blogposts(short_name):
    project, owner, ps = project_by_shortname(short_name)

    if current_user.is_authenticated and current_user.id == owner.id:#관리자일 때
        blogposts = blog_repo.get_blogposts(project.id, owner)
        anno_posts = blog_repo.filter_by(project_id=project.id, user_id=owner.id,
                                         published=True)
        temp_posts = blog_repo.filter_by(project_id=project.id, published=False)
    else:
        blogposts = blog_repo.get_blogposts(project.id, owner)
        anno_posts = blog_repo.filter_by(project_id=project.id, user_id=owner.id,
                                         published=True)
        temp_posts = blog_repo.filter_by(project_id=project.id, user_id=current_user.id,
                                        published=False)

    if project.needs_password():
        redirect_to_password = _check_if_redirect_to_password(project)
        if redirect_to_password:
            return redirect_to_password
    else:
        ensure_authorized_to('read', Blogpost, project_id=project.id)
    pro = pro_features()
    project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)

    project_sanitized, owner_sanitized = sanitize_project_owner(project,
                                                                owner,
                                                                current_user,
                                                                ps)
    
    response = dict(template='projects/blog.html',
                    project=project_sanitized,
                    owner=owner_sanitized,
                    blogposts=blogposts,
                    anno_posts=anno_posts,
                    temp_posts=temp_posts,
                    overall_progress=ps.overall_progress,
                    n_tasks=ps.n_tasks,
                    n_task_runs=ps.n_task_runs,
                    n_completed_tasks=ps.n_completed_tasks,
                    n_volunteers=ps.n_volunteers,
                    pro_features=pro)
    return handle_content_type(response)


@blueprint.route('/<short_name>/<int:id>', methods=['GET'])
def show_blogpost(short_name, id):
    project, owner, ps = project_by_shortname(short_name)

    blogpost = blog_repo.get_by(id=id, project_id=project.id)
    if blogpost is None:
        raise abort(404)

    if request.method == 'GET':
        if request.args.get('state') == "insert":
            user_name = request.args.get('user_name')
            comment = request.args.get('comment')
            import datetime
            now = datetime.datetime.now()
            created = now.strftime('%Y-%m-%dT%H:%M:%S.%f')
            blogpost.info[user_name+'/'+comment] = created
            blog_repo.save(blogpost)
            return user_name
        elif request.args.get('state') == "delete":
            del_data = request.args.get('data')
            del blogpost.info[del_data]
            blog_repo.save(blogpost)
            return del_data
        elif request.args.get('state') == "update":
            key = request.args.get('key')
            created = blogpost.info[key]
            data = request.args.get('data')
            del blogpost.info[key]
            blogpost.info[data] = created
            blog_repo.save(blogpost)
            return data

    if current_user.is_anonymous and blogpost.published is False:
        raise abort(404)
    if (blogpost.published is False and
            current_user.is_authenticated and
            current_user.id != blogpost.user_id):
        raise abort(404)
    if project.needs_password():
        redirect_to_password = _check_if_redirect_to_password(project)
        if redirect_to_password:
            return redirect_to_password
    else:
        ensure_authorized_to('read', blogpost)
    pro = pro_features()
    project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)

    def blog_comment(blogpost, count):
        info = sorted(blogpost.info.items(), key=lambda item: item[1])
        comment = []
        for blog in info:
            temp = blog[0].split('/')
            temp.append(blog[1])
            comment.append(temp)
            count = count + 1
        return comment, count

    comment = None
    count = 0
    if blogpost.info != None:
        comment,count = blog_comment(blogpost, count)

    return render_template('projects/blog_post.html',
                           project=project,
                           owner=owner,
                           blogpost=blogpost,
                           comments=comment,
                           counts=count,
                           overall_progress=ps.overall_progress,
                           n_tasks=ps.n_tasks,
                           n_task_runs=ps.n_task_runs,
                           n_completed_tasks=ps.n_completed_tasks,
                           n_volunteers=ps.n_volunteers,
                           pro_features=pro)


@blueprint.route('/<short_name>/new-blogpost', methods=['GET', 'POST'])
@login_required
def new_blogpost(short_name):
    if request.method == 'GET':
        if request.args.get('user_id') != None:
            new_blog = blog_repo.get_lately(request.args.get('user_id'))
            blog_id = 0
            for row in new_blog:
                blog_id = row
            url = url_for('.show_blogpost', short_name=short_name, id=blog_id)
            return url

    pro = pro_features()

    def respond():
        dict_project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)
        response = dict(template='projects/new_blogpost.html',
                        title=gettext("Write a new post"),
                        form=form,
                        project=project_sanitized,
                        owner=owner_sanitized,
                        overall_progress=ps.overall_progress,
                        n_tasks=ps.n_tasks,
                        n_task_runs=ps.n_task_runs,
                        n_completed_tasks=cached_projects.n_completed_tasks(dict_project.get('id')),
                        n_volunteers=cached_projects.n_volunteers(dict_project.get('id')),
                        pro_features=pro)
        return handle_content_type(response)

    project, owner, ps = project_by_shortname(short_name)


    form = BlogpostForm(request.form)
    del form.id

    project_sanitized, owner_sanitized = sanitize_project_owner(project, owner,
                                                                current_user,
                                                                ps)

    if request.method != 'POST':
        ensure_authorized_to('create', Blogpost, project_id=project.id)
        return respond()

    if not form.validate():
        #flash(gettext('Please correct the errors'), 'error')
        flash(gettext('오류를 수정해주세요'), 'error')
        return respond()
    blogpost = Blogpost(title=form.title.data,
                        body=form.body.data,
                        user_id=current_user.id,
                        project_id=project.id)
    ensure_authorized_to('create', blogpost)
    blog_repo.save(blogpost)

    #msg_1 = gettext('Blog post created!')
    msg_1 = gettext('게시글 생성 완료!')
    flash(Markup('<i class="icon-ok"></i> {}').format(msg_1), 'success')

    return redirect(url_for('.show_blogposts', short_name=short_name))


@blueprint.route('/<short_name>/<int:id>/update', methods=['GET', 'POST'])
@login_required
def update_blogpost(short_name, id):
    if request.method == 'GET':
        if request.args.get('user_id') != None:
            url = url_for('.show_blogpost', short_name=short_name, id=id)
            return url

    project, owner, ps = project_by_shortname(short_name)

    pro = pro_features()
    blogpost = blog_repo.get_by(id=id, project_id=project.id)
    if blogpost is None:
        raise abort(404)

    def respond():
        return render_template('projects/update_blogpost.html',
                               title=gettext("Edit a post"),
                               form=form, project=project, owner=owner,
                               blogpost=blogpost,
                               overall_progress=ps.overall_progress,
                               n_task_runs=ps.n_task_runs,
                               n_completed_tasks=cached_projects.n_completed_tasks(project.id),
                               n_volunteers=cached_projects.n_volunteers(project.id),
                               pro_features=pro)

    form = BlogpostForm()

    if request.method != 'POST':
        ensure_authorized_to('update', blogpost)
        form = BlogpostForm(obj=blogpost)
        return respond()

    if not form.validate():
        #flash(gettext('Please correct the errors'), 'error')
        flash(gettext('오류를 수정해주세요'), 'error')
        return respond()

    ensure_authorized_to('update', blogpost)
    blogpost = Blogpost(id=form.id.data,
                        title=form.title.data,
                        body=form.body.data,
                        user_id=current_user.id,
                        project_id=project.id,
                        published=form.published.data)
    blog_repo.update(blogpost)

    #msg_1 = gettext('Blog post updated!')
    msg_1 = gettext('게시글 업데이트 완료!')
    flash(Markup('<i class="icon-ok"></i> {}').format(msg_1), 'success')

    return redirect(url_for('.show_blogposts', short_name=short_name))


@blueprint.route('/<short_name>/<int:id>/delete', methods=['POST'])
@login_required
def delete_blogpost(short_name, id):
    project = project_by_shortname(short_name)[0]
    blogpost = blog_repo.get_by(id=id, project_id=project.id)
    if blogpost is None:
        raise abort(404)

    ensure_authorized_to('delete', blogpost)
    blog_repo.delete(blogpost)
    #msg_1 = gettext('Blog post deleted!')
    msg_1 = gettext('게시글 삭제 완료!')
    flash(Markup('<i class="icon-ok"></i> {}').format(msg_1), 'success')
    return redirect(url_for('.show_blogposts', short_name=short_name))


def _check_if_redirect_to_password(project):
    cookie_exp = current_app.config.get('PASSWD_COOKIE_TIMEOUT')
    passwd_mngr = ProjectPasswdManager(CookieHandler(request, signer, cookie_exp))
    if passwd_mngr.password_needed(project, get_user_id_or_ip()):
        return redirect(url_for('.password_required',
                                short_name=project.short_name, next=request.path))


@blueprint.route('/<short_name>/auditlog')
@login_required
def auditlog(short_name):
    pro = pro_features()
    if not pro['auditlog_enabled']:
        raise abort(403)

    project, owner, ps = project_by_shortname(short_name)


    ensure_authorized_to('read', Auditlog, project_id=project.id)
    logs = auditlogger.get_project_logs(project.id)
    project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)
    return render_template('projects/auditlog.html', project=project,
                           owner=owner, logs=logs,
                           overall_progress=ps.overall_progress,
                           n_tasks=ps.n_tasks,
                           n_task_runs=ps.n_task_runs,
                           n_completed_tasks=ps.n_completed_tasks,
                           n_volunteers=ps.n_volunteers,
                           pro_features=pro)


@blueprint.route('/<short_name>/publish', methods=['GET', 'POST'])
@login_required
def publish(short_name):

    project, owner, ps = project_by_shortname(short_name)
    project_sanitized, owner_sanitized = sanitize_project_owner(project, owner,
                                                                current_user,
                                                                ps)
    pro = pro_features()
    ensure_authorized_to('publish', project)
    if request.method == 'GET':
        template_args = {"project": project_sanitized,
                         "pro_features": pro,
                         "csrf": generate_csrf()}
        response = dict(template='/projects/publish.html', **template_args)
        return handle_content_type(response)

    if project.published is False:
        project.published = True
        project_repo.save(project)
        task_repo.delete_taskruns_from_project(project)
        result_repo.delete_results_from_project(project)
        webhook_repo.delete_entries_from_project(project)
        auditlogger.log_event(project, current_user,
                              'update', 'published', False, True)
        #flash(gettext('Project published! Volunteers will now be able to help you!'))
        flash(gettext('프로젝트가 공개되었습니다!'))
    else:
        #flash(gettext('Project already published'))
        flash(gettext('이미 공개된 프로젝트입니다'))
    return redirect(url_for('.details', short_name=project.short_name))


def project_event_stream(short_name, channel_type):
    """Event stream for pub/sub notifications."""
    pubsub = sentinel.master.pubsub()
    channel = "channel_%s_%s" % (channel_type, short_name)
    pubsub.subscribe(channel)
    for message in pubsub.listen():
        yield 'data: %s\n\n' % message['data']


@blueprint.route('/<short_name>/privatestream')
@login_required
def project_stream_uri_private(short_name):
    """Returns stream."""
    if current_app.config.get('SSE'):
        project, owner, ps = project_by_shortname(short_name)

        if current_user.id in project.owners_ids or current_user.admin:
            return Response(project_event_stream(short_name, 'private'),
                            mimetype="text/event-stream",
                            direct_passthrough=True)
        else:
            return abort(403)
    else:
        return abort(404)


@blueprint.route('/<short_name>/publicstream')
def project_stream_uri_public(short_name):
    """Returns stream."""
    if current_app.config.get('SSE'):
        project, owner, ps = project_by_shortname(short_name)
        return Response(project_event_stream(short_name, 'public'),
                        mimetype="text/event-stream")
    else:
        abort(404)


@blueprint.route('/<short_name>/webhook', defaults={'oid': None})
@blueprint.route('/<short_name>/webhook/<int:oid>', methods=['GET', 'POST'])
@login_required
def webhook_handler(short_name, oid=None):
    project, owner, ps = project_by_shortname(short_name)

    pro = pro_features()
    if not pro['webhooks_enabled']:
        raise abort(403)

    responses = webhook_repo.filter_by(project_id=project.id)
    if request.method == 'POST' and oid:
        tmp = webhook_repo.get(oid)
        if tmp:
            webhook_queue.enqueue(webhook, project.webhook,
                                  tmp.payload, tmp.id, True)
            return json.dumps(tmp.dictize())
        else:
            abort(404)

    ensure_authorized_to('read', Webhook, project_id=project.id)
    redirect_to_password = _check_if_redirect_to_password(project)
    if redirect_to_password:
        return redirect_to_password

    if request.method == 'GET' and request.args.get('all'):
        for wh in responses:
            webhook_queue.enqueue(webhook, project.webhook,
                                  wh.payload, wh.id, True)
        flash('All webhooks enqueued')

    if request.method == 'GET' and request.args.get('failed'):
        for wh in responses:
            if wh.response_status_code != 200:
                webhook_queue.enqueue(webhook, project.webhook,
                                      wh.payload, wh.id, True)
        flash('All webhooks enqueued')

    project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)

    return render_template('projects/webhook.html', project=project,
                           owner=owner, responses=responses,
                           overall_progress=ps.overall_progress,
                           n_tasks=ps.n_tasks,
                           n_task_runs=ps.n_task_runs,
                           n_completed_tasks=ps.n_completed_tasks,
                           n_volunteers=ps.n_volunteers,
                           pro_features=pro)


@blueprint.route('/<short_name>/results')
def results(short_name):
    """Results page for the project."""

    project, owner, ps = project_by_shortname(short_name)

    title = project_title(project, "Results")

    ensure_authorized_to('read', project)

    pro = pro_features()

    title = project_title(project, None)
    project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)

    project_sanitized, owner_sanitized = sanitize_project_owner(project, owner,
                                                                current_user,
                                                                ps)

    template_args = {"project": project_sanitized,
                     "title": title,
                     "owner": owner_sanitized,
                     "n_tasks": ps.n_tasks,
                     "n_task_runs": ps.n_task_runs,
                     "overall_progress": ps.overall_progress,
                     "last_activity": ps.last_activity,
                     "n_completed_tasks": ps.n_completed_tasks,
                     "n_volunteers": ps.n_volunteers,
                     "pro_features": pro,
                     "n_results": ps.n_results}

    response = dict(template = '/projects/results.html', **template_args)

    return handle_content_type(response)


@blueprint.route('/<short_name>/resetsecretkey', methods=['POST'])
@login_required
def reset_secret_key(short_name):
    """
    Reset Project key.

    """

    project, owner, ps = project_by_shortname(short_name)


    title = project_title(project, "Results")

    ensure_authorized_to('update', project)

    project.secret_key = make_uuid()
    project_repo.update(project)
    #msg = gettext('New secret key generated')
    msg = gettext('새로운 키 생성')
    flash(msg, 'success')
    return redirect_content_type(url_for('.update', short_name=short_name))


@blueprint.route('/<short_name>/transferownership', methods=['GET', 'POST'])
@login_required
def transfer_ownership(short_name):
    """Transfer project ownership."""

    project, owner, ps = project_by_shortname(short_name)

    pro = pro_features()

    title = project_title(project, "Results")

    ensure_authorized_to('update', project)

    form = TransferOwnershipForm(request.body)

    if request.method == 'POST' and form.validate():
        new_owner = user_repo.filter_by(email_addr=form.email_addr.data)
        if len(new_owner) == 1:
            new_owner = new_owner[0]
            project.owner_id = new_owner.id
            project.owners_ids = [new_owner.id]
            project_repo.update(project)
            #msg = gettext("Project owner updated")
            msg = gettext("프로젝트 관리자 업데이트")
            flash(msg, 'info')
            return redirect_content_type(url_for('.details',
                                                 short_name=short_name))
        else:
            #msg = gettext("New project owner not found by email")
            msg = gettext("이메일과 일치하는 사용자를 찾을 수 없습니다")
            flash(msg, 'info')
            return redirect_content_type(url_for('.transfer_ownership',
                                                 short_name=short_name))
    else:
        owner_serialized = cached_users.get_user_summary(owner.name)
        project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)
        response = dict(template='/projects/transferownership.html',
                        project=project,
                        owner=owner_serialized,
                        n_tasks=ps.n_tasks,
                        overall_progress=ps.overall_progress,
                        n_task_runs=ps.n_task_runs,
                        last_activity=ps.last_activity,
                        n_completed_tasks=ps.n_completed_tasks,
                        n_volunteers=ps.n_volunteers,
                        title=title,
                        pro_features=pro,
                        form=form,
                        target='.transfer_ownership')
        return handle_content_type(response)


@blueprint.route('/<short_name>/coowners', methods=['GET', 'POST'])
@login_required
def coowners(short_name):
    """Manage coowners of a project."""
    form = SearchForm(request.form)
    project = project_repo.get_by_shortname(short_name)
    owners = user_repo.get_users(project.owners_ids)
    pub_owners = [user.to_public_json() for user in owners]
    for owner, p_owner in zip(owners, pub_owners):
        if owner.id == project.owner_id:
            p_owner['is_creator'] = True

    ensure_authorized_to('read', project)
    ensure_authorized_to('update', project)

    response = dict(
        template='/projects/coowners.html',
        project=project.to_public_json(),
        coowners=pub_owners,
        title=gettext("Manage Co-owners"),
        form=form,
        pro_features=pro_features()
    )

    if request.method == 'POST' and form.user.data:
        query = form.user.data
        user = user_repo.get_by_name(query)

        if not user or user.id == current_user.id:
            #flash(markup.format(gettext("Ooops!"),
            #                    gettext("We didn't find a user matching your query:"),
            flash(Markup(gettext("일치하는 사용자를 찾을 수 없습니다.")))
        else:
            found = user.to_public_json()
            found['is_coowner'] = user.id in project.owners_ids
            found['is_creator'] = user.id == project.owner_id
            response['found'] = found

    return handle_content_type(response)


@blueprint.route('/<short_name>/add_coowner/<user_name>')
@login_required
def add_coowner(short_name, user_name=None):
    """Add project co-owner."""
    project = project_repo.get_by_shortname(short_name)
    user = user_repo.get_by_name(user_name)

    ensure_authorized_to('read', project)
    ensure_authorized_to('update', project)

    if project and user:
        if user.id in project.owners_ids:
            #flash(gettext('User is already an owner'), 'warning')
            flash(gettext("이미 관리자입니다"), 'warning')
        else:
            project.owners_ids.append(user.id)
            project_repo.update(project)
            user.orderer.append(project.id)
            user_repo.update(user)
            #flash(gettext('User was added to list of owners'), 'success')
            flash(gettext('관리자 목록에 추가하였습니다'), 'success')
        return redirect_content_type(url_for(".coowners", short_name=short_name))
    return abort(404)


@blueprint.route('/<short_name>/del_coowner/<user_name>')
@login_required
def del_coowner(short_name, user_name=None):
    """Delete project co-owner."""
    project = project_repo.get_by_shortname(short_name)
    user = user_repo.get_by_name(user_name)

    ensure_authorized_to('read', project)
    ensure_authorized_to('update', project)

    if project and user:
        if user.id == project.owner_id:
            #flash(gettext('Cannot remove project creator'), 'error')
            flash(gettext('프로젝트 생성자를 삭제할 수 없습니다'), 'error')
        elif user.id not in project.owners_ids:
            #flash(gettext('User is not a project owner'), 'error')
            flash(gettext('프로젝트 관리자가 아닙니다'), 'error')
        else:
            project.owners_ids.remove(user.id)
            project_repo.update(project)
            user.orderer.remove(project.id)
            user_repo.update(user)
            #flash(gettext('User was deleted from the list of owners'),
            #      'success')
            flash(gettext('관리자 목록에서 삭제하였습니다'), 'success')
        return redirect_content_type(url_for('.coowners', short_name=short_name))
    return abort(404)


@blueprint.route('/<short_name>/projectreport/export')
@login_required
def export_project_report(short_name):
    """Export individual project information in the given format"""

    project, owner, ps = project_by_shortname(short_name)
    if not current_user.admin and not current_user.id in project.owners_ids:
        return abort(403)

    project_report_csv_exporter = ProjectReportCsvExporter()

    def respond():
        project, owner, ps = project_by_shortname(short_name)
        title = project_title(project, "Settings")
        pro = pro_features()
        project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)
        owner_serialized = cached_users.get_user_summary(owner.name)
        response = dict(template='/projects/settings.html',
                        project=project,
                        owner=owner_serialized,
                        n_tasks=ps.n_tasks,
                        overall_progress=ps.overall_progress,
                        n_task_runs=ps.n_task_runs,
                        last_activity=ps.last_activity,
                        n_completed_tasks=ps.n_completed_tasks,
                        n_volunteers=ps.n_volunteers,
                        title=title,
                        pro_features=pro)
        return handle_content_type(response)


    def respond_csv(ty):
        if ty not in ('project',):
            return abort(404)

        try:
            res = project_report_csv_exporter.response_zip(project, ty)
            return res
        except Exception as e:
            current_app.logger.exception(
                    'CSV Export Failed - Project: {0}, Type: {1} - Error: {2}'
                    .format(project.short_name, ty, e))
            flash(gettext('Error generating project report.'), 'error')
        return abort(500)

    export_formats = ['csv']
    ty = request.args.get('type')
    fmt = request.args.get('format')

    if not (fmt and ty):
        if len(request.args) >= 1:
            return abort(404)
        return respond()

    if fmt not in export_formats:
        abort(415)

    if ty == 'project':
        project = project_repo.get(project.id)
        if project:
            ensure_authorized_to('read', project)

    return {'csv': respond_csv}[fmt](ty)
