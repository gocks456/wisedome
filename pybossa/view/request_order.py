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
import time
import re
import json
import os
import math
import requests
from StringIO import StringIO

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
                          result_repo, webhook_repo, auditlog_repo)
from pybossa.auditlogger import AuditLogger
from pybossa.contributions_guard import ContributionsGuard
from pybossa.default_settings import TIMEOUT
from pybossa.exporter.csv_reports_export import ProjectReportCsvExporter
from jinja2.exceptions import TemplateNotFound


blueprint = Blueprint('request_order', __name__)


@blueprint.route('/')
def index():
    """Render the about template."""
    response = dict(template="/order/index.html")
    return handle_content_type(response)

@blueprint.route('/<short_name>/order')
def show_orderposts(short_name):
    project, owner, ps = project_by_shortname(short_name)

    if current_user.is_authenticated() and current_user.id == owner.id:
        orderposts = order_repo.filter_by(project_id=project.id)
    else:
        orderposts = order_repo.filter_by(project_id=project.id,
                                        published=True)
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

    response = dict(template='projects/order.html',
                    project=project_sanitized,
                    owner=owner_sanitized,
                    orderposts=orderposts,
                    overall_progress=ps.overall_progress,
                    n_tasks=ps.n_tasks,
                    n_task_runs=ps.n_task_runs,
                    n_completed_tasks=ps.n_completed_tasks,
                    n_volunteers=ps.n_volunteers,
                    pro_features=pro)
    return handle_content_type(response)


@blueprint.route('/<short_name>/<int:id>')
def show_orderpost(short_name, id):
    project, owner, ps = project_by_shortname(short_name)

    orderpost = order_repo.get_by(id=id, project_id=project.id)
    if orderpost is None:
        raise abort(404)
    if current_user.is_anonymous() and orderpost.published is False:
        raise abort(404)
    if (orderpost.published is False and
            current_user.is_authenticated() and
            current_user.id != orderpost.user_id):
        raise abort(404)
    if project.needs_password():
        redirect_to_password = _check_if_redirect_to_password(project)
        if redirect_to_password:
            return redirect_to_password
    else:
        ensure_authorized_to('read', orderpost)
    pro = pro_features()
    project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)
    return render_template('projects/order_post.html',
                           project=project,
                           owner=owner,
                           orderpost=orderpost,
                           overall_progress=ps.overall_progress,
                           n_tasks=ps.n_tasks,
                           n_task_runs=ps.n_task_runs,
                           n_completed_tasks=ps.n_completed_tasks,
                           n_volunteers=ps.n_volunteers,
                           pro_features=pro)


@blueprint.route('/<short_name>/new-orderpost', methods=['GET', 'POST'])
@login_required
def new_orderpost(short_name):
    pro = pro_features()

    def respond():
        dict_project = add_custom_contrib_button_to(project, get_user_id_or_ip(), ps=ps)
        response = dict(template='projects/new_orderpost.html',
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
        flash(gettext('Please correct the errors'), 'error')
        return respond()

    orderpost = Blogpost(title=form.title.data,
                        body=form.body.data,
                        user_id=current_user.id,
                        project_id=project.id)
    ensure_authorized_to('create', orderpost)
    order_repo.save(orderpost)

    msg_1 = gettext('Blog post created!')
    flash(Markup('<i class="icon-ok"></i> {}').format(msg_1), 'success')

    return redirect(url_for('.show_orderposts', short_name=short_name))


@blueprint.route('/<short_name>/<int:id>/update', methods=['GET', 'POST'])
@login_required
def update_orderpost(short_name, id):

    project, owner, ps = project_by_shortname(short_name)

    pro = pro_features()
    orderpost = order_repo.get_by(id=id, project_id=project.id)
    if orderpost is None:
        raise abort(404)

    def respond():
        return render_template('projects/update_orderpost.html',
                               title=gettext("Edit a post"),
                               form=form, project=project, owner=owner,
                               orderpost=orderpost,
                               overall_progress=ps.overall_progress,
                               n_task_runs=ps.n_task_runs,
                               n_completed_tasks=cached_projects.n_completed_tasks(project.id),
                               n_volunteers=cached_projects.n_volunteers(project.id),
                               pro_features=pro)

    form = BlogpostForm()

    if request.method != 'POST':
        ensure_authorized_to('update', orderpost)
        form = BlogpostForm(obj=orderpost)
        return respond()

    if not form.validate():
        flash(gettext('Please correct the errors'), 'error')
        return respond()

    ensure_authorized_to('update', orderpost)
    orderpost = Blogpost(id=form.id.data,
                        title=form.title.data,
                        body=form.body.data,
                        user_id=current_user.id,
                        project_id=project.id,
                        published=form.published.data)
    order_repo.update(orderpost)

    msg_1 = gettext('Blog post updated!')
    flash(Markup('<i class="icon-ok"></i> {}').format(msg_1), 'success')

    return redirect(url_for('.show_orderposts', short_name=short_name))


@blueprint.route('/<short_name>/<int:id>/delete', methods=['POST'])
@login_required
def delete_orderpost(short_name, id):
    project = project_by_shortname(short_name)[0]
    orderpost = order_repo.get_by(id=id, project_id=project.id)
    if orderpost is None:
        raise abort(404)

    ensure_authorized_to('delete', orderpost)
    order_repo.delete(orderpost)
    msg_1 = gettext('Blog post deleted!')
    flash(Markup('<i class="icon-ok"></i> {}').format(msg_1), 'success')
    return redirect(url_for('.show_orderposts', short_name=short_name))


def _check_if_redirect_to_password(project):
    cookie_exp = current_app.config.get('PASSWD_COOKIE_TIMEOUT')
    passwd_mngr = ProjectPasswdManager(CookieHandler(request, signer, cookie_exp))
    if passwd_mngr.password_needed(project, get_user_id_or_ip()):
        return redirect(url_for('.password_required',
                                short_name=project.short_name, next=request.path))

@blueprint.route('/neworder', methods=['GET', 'POST'])
def new_order():
    """
    Register method for creating a PYBOSSA account.

    Returns a Jinja2 template

    """
    if current_app.config.get('LDAP_HOST', False):
        return abort(404)
    if not current_app.config.upref_mdata:
        form = RegisterForm(request.body)
    else:
        form = RegisterFormWithUserPrefMetadata(request.body)
        form.set_upref_mdata_choices()

    msg = "I accept receiving emails from %s" % current_app.config.get('BRAND')
    form.consent.label = msg
    if request.method == 'POST' and form.validate():
        if current_app.config.upref_mdata:
            user_pref, metadata = get_user_pref_and_metadata(form.name.data, form)
            account = dict(fullname=form.fullname.data, name=form.name.data,
                           email_addr=form.email_addr.data,
                           password=form.password.data,
                           consent=form.consent.data,
                           user_type=form.user_type.data)
            account['user_pref'] = user_pref
            account['metadata'] = metadata
        else:
            account = dict(fullname=form.fullname.data, name=form.name.data,
                           email_addr=form.email_addr.data,
                           password=form.password.data,
                           consent=form.consent.data)

        confirm_url = get_email_confirmation_url(account)
        if current_app.config.get('ACCOUNT_CONFIRMATION_DISABLED'):
            return _create_account(account)
        msg = dict(subject='Welcome to %s!' % current_app.config.get('BRAND'),
                   recipients=[account['email_addr']],
                   body=render_template('/account/email/validate_account.md',
                                        user=account, confirm_url=confirm_url))
        msg['html'] = markdown(msg['body'])
        mail_queue.enqueue(send_mail, msg)
        data = dict(template='account/account_validation.html',
                    title=gettext("Account validation"),
                    status='sent')
        return handle_content_type(data)
    if request.method == 'POST' and not form.validate():
        flash(gettext('Please correct the errors'), 'error')
    data = dict(template='order/index.html',
                title=gettext("Register"), form=form)
    return handle_content_type(data)

