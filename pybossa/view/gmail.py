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

"""Google view for PYBOSSA."""
from flask import Blueprint, request, url_for, flash, redirect, session, current_app
from flask import abort, render_template
from flask_login import login_user, current_user
from flask_oauthlib.client import OAuthException

from pybossa.core import gmail, user_repo, newsletter, point_repo
from pybossa.model.user import User
from pybossa.model.point import Point
from pybossa.util import get_user_signup_method, username_from_full_name
from pybossa.util import url_for_app_type, handle_content_type, redirect_content_type, admin_required

from pybossa.forms.account_view_forms import APIRegisterForm
# Required to access the config parameters outside a context as we are using
# Flask 0.8
# See http://goo.gl/tbhgF for more info
import requests
import json

blueprint = Blueprint('gmail', __name__)

@admin_required
@blueprint.route('/', methods=['GET', 'POST'])
def login():  # pragma: no cover
	"""Login with Google."""
	user = user_repo.get_by(name='gmail')
	if user is not None:
		return redirect_content_type(url_for('home.home'))

	if not current_app.config.get('LDAP_HOST', False):
		if request.args.get("next"):
			request_token_params = {'scope': 'profile email'}
			gmail.oauth.request_token_params = request_token_params
		callback = url_for('.oauth_authorized', _external=True)
		return gmail.oauth.authorize(callback=callback)
	else:
		return abort(404)

@admin_required
@blueprint.route('/oauth_authorized')
def oauth_authorized():  # pragma: no cover
	"""Authorize Oauth."""
	resp = gmail.oauth.authorized_response()
	print(resp)

	if resp is None or request.args.get('error'):
		flash('You denied the request to sign in.', 'error')
		flash('Reason: ' + request.args['error'], 'error')
		if request.args.get('error'):
			current_app.logger.error(resp)
			return redirect(url_for_app_type('account.signin',
							_hash_last_flash=True))
		next_url = (request.args.get('next') or
					url_for_app_type('home.home', _hash_last_flash=True))
		return redirect(next_url)
	if isinstance(resp, OAuthException):
		flash('Access denied: %s' % resp.message)
		current_app.logger.error(resp)
		next_url = (request.args.get('next') or
					url_for_app_type('home.home', _hash_last_flash=True))
		return redirect(next_url)
	headers = {'Authorization': ' '.join(['OAuth', resp['access_token']])}
	url = 'https://www.googleapis.com/oauth2/v1/userinfo'
	
	try:
		r = requests.get(url, headers=headers)
	except requests.exceptions.http_error:
		# Unauthorized - bad token
		if r.status_code == 401:
			return redirect(url_for_app_type('home.home'))
		return r.content

	access_token = resp['access_token']
	session['oauth_token'] = access_token
	user_data = json.loads(r.content)

	print(r.content.decode('utf-8'))
	user_id = user_data["id"]

	user= user_repo.get_by(google_user_id=user_id)
	if user is not None:
		user.info['google_token']['oauth_token'] = access_token
		user_repo.save(user)
		return redirect_content_type(url_for('home.home'))

	resp['refresh_token']

	google_token = dict(oauth_token=access_token, refresh_token=refresh_token)

	user = User(fullname='gmail',
				name='gmail',
				email_addr=user_data["email"],
				google_user_id=user_id,
				sex='M',
				birth='20000000',
				info=dict(google_token=google_token))
	user_repo.save(user)

	return user_id


from apiclient import errors
from email.mime.text import MIMEText
import base64

def create_message(sender, to, subject, message_text):
	"""Create a message for an email.
	Args:
		sender: Email address of the sender.
		to: Email address of the receiver.
		subject: The subject of the email message.
		message_text: The text of the email message.
	Returns:
		An object containing a base64url encoded email object.
	"""
	message = MIMEText(message_text, 'html')
	message['to'] = to
	message['from'] = sender
	message['subject'] = subject
	return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')}

def send_message(service, user_id, message):
	"""Send an email message.
	Args:
		service: Authorized Gmail API service instance.
		user_id: User's email address. The special value "me"
		can be used to indicate the authenticated user.
		message: Message to be sent.
	Returns:
		Sent Message.
	"""

	try:
		message = (service.users().messages().send(userId=user_id, body=message)
							 .execute())
		print('Message Id: %s' % message['id'])
		return message
	except errors.HttpError as error:
		print('An error occurred: %s' % error)


def get_google_token():
	# google_token 가져오기

	user = user_repo.get_by(google_user_id=current_app.config['GMAIL_ID'])
	google_token = user.info['google_token']
	return google_token

def send(message, token):
	headers = {
				'Authorization': ' '.join(['Bearer', token]),
				'Content-Type': 'application/json',
				'Accept': 'application/json'
				}

	params = {
			('alt', 'json'),
			('upload_protocol', 'post')
			}
	url = 'https://www.googleapis.com/gmail/v1/users/me/messages/send'

	try:
		r = requests.post(url, headers=headers, params=params, data=json.dumps(message))
		return r
	except requests.exceptions.http_error:
		# Unauthorized - bad token
		if r.status_code == 401:
			return redirect(url_for_app_type('account.signin'))
		return r.content


@blueprint.route('/auth_msg', methods=['POST'])
def auth_msg():
	access_num = request.form['random_num']

	if access_num == "0":
		return "CAN'T SEND"


	EMAIL_FROM = current_app.config['GMAIL']
	EMAIL_TO = request.form['email']
	EMAIL_SUBJECT = 'Wisedome 이메일 인증'
	EMAIL_CONTENT = '이메일 인증번호는 다음과 같습니다.<br><br>인증번호: ' + access_num

	# Call the Gmail API
	message = create_message(EMAIL_FROM, EMAIL_TO, EMAIL_SUBJECT, EMAIL_CONTENT)
	return send_mail(message)


def send_mail(message):
	# mail 전송
	google_token = get_google_token()

	r = send(message, google_token['oauth_token'])

	print(r.content.decode('utf-8'))

	return_send = json.loads(r.content)

	if not "error" in return_send.keys():
		return 'SEND'

	else:
		refresh_token = google_token['refresh_token']

		params = {
				'client_id': current_app.config['GMAIL_CLIENT_ID'],
				'client_secret': current_app.config['GMAIL_CLIENT_SECRET'],
				'refresh_token': refresh_token,
				'grant_type' : 'refresh_token'
				}
		
		url = 'https://oauth2.googleapis.com/token'

		try:
			r = requests.post(url, params=params)
		except requests.exceptions.http_error:
			# Unauthorized - bad token
			if r.status_code == 401:
				return redirect(url_for_app_type('admin.index'))
			return r.content

		r=json.loads(r.content)

		access_token = r['access_token']

		user= user_repo.get_by(google_user_id=current_app.config['GMAIL_ID'])

		google_token = user.info
		google_token['google_token']['oauth_token'] = access_token
		user.info = google_token
		user_repo.update_token(user)

		r = send(message, access_token)

		return_send = json.loads(r.content)

		if not "error" in return_send.keys():
			return "SEND"
		return "CAN'T SEND"
