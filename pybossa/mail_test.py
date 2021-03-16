from googleapiclient.discovery import build
from apiclient import errors
from httplib2 import Http
from email.mime.text import MIMEText
import base64
from google.oauth2 import service_account
import json

# Email variables. Modify this!
EMAIL_FROM = 'gocks4560@gmail.com'
EMAIL_TO = 'gocks456@naver.com'
EMAIL_SUBJECT = 'Hello	from Lyfepedia!'
EMAIL_CONTENT = 'Hello, this is a test\nLyfepedia\nhttps://lyfepedia.com'



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
	message = MIMEText(message_text)
	message['to'] = to
	message['from'] = sender
	message['subject'] = subject
	print(message)
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

def service_account_login():
	SCOPES = ['https://www.googleapis.com/auth/gmail.send']
	SERVICE_ACCOUNT_FILE = json.load(open('./onyx-course-300007-a58bc5d32008.json','r'))
	print(SERVICE_ACCOUNT_FILE)

	#SERVICE_ACCOUNT_FILE["web"]["client_email"] = EMAIL_FROM

	credentials = service_account.Credentials.from_service_account_info(
					SERVICE_ACCOUNT_FILE, scopes=SCOPES)
	delegated_credentials = credentials.with_subject(EMAIL_FROM)
	service = build('gmail', 'v1', credentials=delegated_credentials)
	print(service)
	return service


service = service_account_login()
# Call the Gmail API
message = create_message(EMAIL_FROM, EMAIL_TO, EMAIL_SUBJECT, EMAIL_CONTENT)
sent = send_message(service,'me', message)
