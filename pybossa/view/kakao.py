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

"""Kakao view for PYBOSSA."""
from flask import Blueprint, request, url_for, flash, redirect, session, current_app
from flask import abort
from flask_login import login_user, current_user
from flask_oauthlib.client import OAuthException

from pybossa.core import kakao, user_repo, newsletter, point_repo
from pybossa.model.user import User
from pybossa.model.point import Point
from pybossa.util import get_user_signup_method, username_from_full_name
from pybossa.util import url_for_app_type, handle_content_type, redirect_content_type

from pybossa.forms.account_view_forms import APIRegisterForm

import requests

blueprint = Blueprint('kakao', __name__)


@blueprint.route('/', methods=['GET', 'POST'])
def login():  # pragma: no cover
    """Login with Kakao."""
    if not current_app.config.get('LDAP_HOST', False):
        if request.args.get("next"):
            request_token_params = {'scope': 'profile email'}
            kakao.oauth.request_token_params = request_token_params
        callback = url_for('.oauth_authorized', _external=True)
        return kakao.oauth.authorize(callback=callback)
    else:
        return abort(404)


@kakao.oauth.tokengetter
def get_kakao_token():  # pragma: no cover
    """Get Kakao Token from session."""
    if current_user.is_anonymous:
        return session.get('oauth_token')
    else:
        return (current_user.info['kakao_token']['oauth_token'], '')


@blueprint.route('/oauth_authorized')
def oauth_authorized():  # pragma: no cover
    """Authorize Oauth."""
    resp = kakao.oauth.authorized_response()
    print(resp)

    if resp is None or request.args.get('error'):
        #flash('You denied the request to sign in.', 'error')
        flash('요청 거부')
        #flash('Reason: ' + request.args['error'], 'error')
        if request.args.get('error'):
            current_app.logger.error(resp)
            return redirect(url_for_app_type('account.signin',
                            _hash_last_flash=True))
        next_url = (request.args.get('next') or
                    url_for_app_type('home.home', _hash_last_flash=True))
        return redirect(next_url)
    if isinstance(resp, OAuthException):
        flash('Access denied: %s' % resp.message)
        flash('접근 오류')
        current_app.logger.error(resp)
        next_url = (request.args.get('next') or
                    url_for_app_type('home.home', _hash_last_flash=True))
        return redirect(next_url)
    headers = {'Authorization': ' '.join(['Bearer', resp['access_token']])}
    url = 'https://kapi.kakao.com/v2/user/me'
    try:
        r = requests.get(url, headers=headers)
    except requests.exceptions.http_error:
        # Unauthorized - bad token
        if r.status_code == 401:
            return redirect(url_for_app_type('account.signin'))
        return r.content

    import json

    access_token = resp['access_token']
    session['oauth_token'] = access_token
    user_data = json.loads(r.content)

    with open('./kakao_log.json', 'a') as output_file:
        print(json.dump(user_data, output_file, indent="\t", ensure_ascii=False))

    if user_data["kakao_account"]["email_needs_agreement"]:
        form = APIRegisterForm(request.body)
        form.locale.data = "ko"
        form.api_id.data = user_data["id"]
        form.api_token.data = access_token

        data = dict(template='new_design/register/kakao_no_email.html', form=form)
        return handle_content_type(data)

    user = user_repo.get_by(kakao_user_id=user_data['id'])
    if user is not None:
        kakao_token = dict(oauth_token=access_token)
        user.info['kakao_token'] = kakao_token
        user_repo.save(user)
        return _sign_in_user(user)

    user_form = user_data_parser(user_data["kakao_account"], user_data["id"], access_token)

    data = dict(template='new_design/register/kakao.html', form=user_form)
    return handle_content_type(data)

@blueprint.route('/register', methods=['POST'])
def register():
    form = APIRegisterForm(request.body)

    if form.validate():
        kakao_token = dict(oauth_token=form.api_token.data)
        info = dict(kakao_token=kakao_token)
        user = User(fullname=form.fullname.data,
                    name=form.name.data,
                    email_addr=form.email_addr.data,
                    kakao_user_id=form.api_id.data,
                    sex=form.sex.data,
                    birth=(form.year.data + form.month.data + form.day.data),
                    locale=form.locale.data,
                    info=info)
        print(user)
        user_repo.save(user)
        _create_point(user.id)
        return _sign_in_user(user)

    sex=form.sex.data
    year=form.year.data
    month=form.month.data
    day=form.day.data
    data = dict(template='new_design/register/kakao.html', form=form, sex=sex, year=year, month=month, day=day)
    return handle_content_type(data)

def user_data_parser(data, api_id, access_token):
    form = APIRegisterForm(request.body)

    #form.name.data = data["profile"]["nickname"]
    form.email_addr.data = data["email"]
    form.locale.data = "ko"
    form.api_id.data = api_id
    form.api_token.data = access_token

    return form

def _sign_in_user(user):
    login_user(user, remember=True)
    return redirect_content_type(url_for("home.home"))

def _create_point(user_id):
    new_point = Point(user_id=user_id)
    point_repo.save(new_point)
    return user_id
