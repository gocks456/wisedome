# -* -coding: utf8 -*-
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
"""Admin view for PYBOSSA."""
import sys
from rq import Queue
from flask import Blueprint
from flask import render_template
from flask import request
from flask import abort
from flask import flash
from flask import redirect
from flask import url_for
from flask import current_app
from flask import Response
from flask import Markup
from flask_login import login_required, current_user
from flask_babel import gettext
from flask_wtf.csrf import generate_csrf
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import ProgrammingError
import pandas as pd
import datetime

from pybossa.model.category import Category
from pybossa.model.announcement import Announcement
from pybossa.util import admin_required, handle_content_type
from pybossa.util import redirect_content_type
from pybossa.cache import projects as cached_projects
from pybossa.cache import categories as cached_cat
from pybossa.cache import users as cached_users
from pybossa.auth import ensure_authorized_to
from pybossa.core import announcement_repo, project_repo, user_repo, task_repo, project_stats_repo
from pybossa.feed import get_update_feed
import pybossa.dashboard.data as dashb
from pybossa.jobs import get_dashboard_jobs
import json
from io import StringIO

from pybossa.forms.admin_view_forms import *
from pybossa.forms.orderer_view_forms import *
from pybossa.news import NOTIFY_ADMIN

from pybossa.backup.manage_postgres_db import *
import os


blueprint = Blueprint('orderer', __name__)

def format_error(msg, status_code):
    """Return error as a JSON response."""
    error = dict(error=msg,
                 status_code=status_code)
    return Response(json.dumps(error), status=status_code,
                    mimetype='application/json')

@blueprint.route('/')
@login_required
def index():
    # admin은 관리자 목록으로
    if current_user.admin:
        return redirect_content_type(url_for('orderer.admin'))
    elif current_user.orderer:
        return redirect_content_type(url_for('orderer.orderer'))
    else:
        flash(Markup(gettext("발주자가 아닙니다.")))
        return redirect_content_type(url_for('home.home'))
    # orderer은 발주자 개인의 발주한 프로젝트 목록으로
    # 둘다 아닐 때 X


def gettime():
    now = datetime.datetime.now()
    return now.strftime('%Y-%m-%dT%H:%M:%S.%f')

@blueprint.route('/admin', methods=['GET', 'POST']) #관리자 페이지
@login_required
@admin_required
def admin():
    """Manage users of PYBOSSA."""
    form = OrderSearchForm(request.body)

    projects = cached_projects.get_orderer_projects()

    if request.method == 'POST' and form.project.data:
        query = form.project.data
        found = [project for project in project_repo.search_by_name(query)
                 if len(project.owners_ids) == 1]
        if not found:
            flash(Markup(gettext("일치하는 프로젝트를 찾을 수 없습니다.")))
        response = dict(template='/orderer/admin.html', current_user=current_user, 
                        projects=projects, found=found, form=form)
        return handle_content_type(response)

    response = dict(template='/orderer/admin.html', current_user=current_user,
                    projects=projects, found=[], form=form)
    return handle_content_type(response)

@blueprint.route('/orderer', methods=['GET']) #발주자 페이지
@login_required
def orderer():
    all_projects = cached_projects.get_orderer_projects()
    projects = []

    for row in all_projects:
        for name in row['users_fullname']:
            if name == current_user.fullname:
                task = task_repo.get_task_by(project_id=row['id'])
                ps = project_stats_repo.get(row['id'])
                row['progress_rate'] = 0.0
                if ps.n_tasks != 0:
                    row['progress_rate'] = round((ps.n_task_runs / (ps.n_tasks * task.n_answers) * 100), 2)
                projects.append(row)
    response = dict(template='/orderer/orderer.html', current_user=current_user,  projects=projects)
    return handle_content_type(response)
