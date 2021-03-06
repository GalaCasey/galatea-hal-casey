import os
import logging
import json
import httplib2
import base64
import re
import uuid
from uuid import uuid4
from email.mime.text import MIMEText
from state import WaitState
from intenthandlers.utils import get_highest_confidence_entity
from cryptography.fernet import Fernet, InvalidToken
from oauth2client import client
from slack_clients import is_direct_message
from apiclient import discovery

logger = logging.getLogger(__name__)

SCOPES = 'https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/calendar https://mail.google.com/' \
         ' https://www.googleapis.com/auth/gmail.compose https://www.googleapis.com/auth/spreadsheets'


class GoogleCredentials(object):
    """
    GoogleCredentials creates and holds credential objects used with Google OAuth. In addition, it handles encrypting
    and decrypting state uuids as they are passed through the Google environment
    """
    def __init__(self, msg_writer, slack_client):
        self.msg_writer = msg_writer
        self.slack_client = slack_client
        self.default_user = slack_client.get_id_from_user_name(os.getenv("DEFAULT_USER", ""))
        # The following two lines are used to typecast the string env variable to a base64 accepted by Fernet
        b_key = base64.urlsafe_b64decode(os.getenv('FERNET_KEY', ""))
        key = base64.urlsafe_b64encode(b_key)
        logger.info("Fernet Key {}".format(key))
        try:
            self.crypt = Fernet(key)
        except ValueError:
            logger.error("Null decryption key given")
        self._credentials_dict = {}

    def get_credential(self, event, state_id, user=None):
        """
        Returns either the user's credentials, or starts the credentialing process if no credentials can be found
        :return: a credentials object, or None if there is no credentials associated with the user
        """
        if user is None:
            user = self.default_user
        try:
            if self._credentials_dict[user].access_token_expired:
                raise GoogleAccessError
            return self._credentials_dict[user]
        except KeyError or GoogleAccessError:
            # create and encrypt state
            state = {'state_id': str(state_id.hex), 'user_id': user}
            encrypted_state = self.crypt.encrypt(json.dumps(state).encode('utf-8'))

            # generate flow, and begin auth
            flow = client.OAuth2WebServerFlow(client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
                                              client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
                                              scope=SCOPES,
                                              redirect_uri=os.getenv("CALLBACK_URI", ""))
            flow.params['access_type'] = 'offline'
            flow.params['prompt'] = 'consent'
            logger.info("flow {}".format(flow.params))
            auth_uri = flow.step1_get_authorize_url(state=encrypted_state)
            if not is_direct_message(event['channel']):
                self.msg_writer.send_message(event['channel'],
                                             "I'll send you the authorization link in a direct message")
            channel = event['user_dm']
            self.msg_writer.send_message_with_attachments(channel, "Authorization Link", [{'text': "<{}|Click here to authorize>".format(auth_uri)}])
            return None

    # This function feels really janky
    def add_credential_return_state_id(self, credentials, state):
        """
        :param credentials: an actual credentials object as returned by flow.step2_exchange from the oauth library
        :param state: An encrypted string representing a slack user ID and a WaitState UUID.
        NOTE: this has the major, and important side effect, of storing the user's credentials in the credentials dict
        :return: the UUID representing the WaitState
        """
        try:
            raw_string = self.crypt.decrypt(state.encode('utf-8'))
        except InvalidToken:
            logger.error("Invalid decryption key given")
            return

        state_json = json.loads(raw_string.decode('ascii'))
        user_id = state_json.get('user_id')
        self._credentials_dict.update({user_id: credentials})

        return uuid.UUID(state_json.get('state_id'))

    def return_state_id(self, state):
        try:
            raw_string = self.crypt.decrypt(state.encode('utf-8'))
        except InvalidToken:
            logger.error("Invalid decryption key given")
            return

        state_json = json.loads(raw_string.decode('ascii'))

        return uuid.UUID(state_json.get('state_id'))


def send_email(msg_writer, event, wit_entities, credentials):
    """
    :param msg_writer: A message writer used to write output to slack
    :param event: The triggering event
    :param wit_entities: The entities of the wit response
    :param credentials: A Google Credentials object used to validate with google Oauth
    send_email generates an email from the message text and sends it to the indicated email address
    :return: A WaitState if the user is not authenticated, nothing if they are
    """
    state_id = uuid4()
    current_creds = credentials.get_credential(event, state_id, user=event['user'])
    if current_creds is None:
        state = WaitState(build_uuid=state_id, intent_value='send-email', event=event,
                          wit_entities=wit_entities, credentials=credentials)
        return state
    http = current_creds.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)

    msg_text = event['cleaned_text']
    email_string = "<mailto:.*@.*\..*\|.*@.*\..*>"  # matches <mailto:example@sample.com|example@sample.com>
    string_cleaner = re.compile(email_string)
    cleaned_msg_text = string_cleaner.sub("", msg_text)
    msg_to = get_highest_confidence_entity(wit_entities, 'email')['value']
    if not msg_to:
        msg_writer.send_message(event['channel'], "I can't understand where you want me to send the message, sorry")
        return

    message = MIMEText(cleaned_msg_text)
    message['to'] = msg_to
    message['from'] = "{}@galatea-associates.com".format(event['user_name']['profile']['last_name'])
    message['subject'] = "Message via Hal from {}".format(event['user_name']['profile']['real_name'])

    message_encoded = {'raw': base64.urlsafe_b64encode(message.as_string().encode('utf-8')).decode('utf-8')}

    service.users().messages().send(userId="me", body=message_encoded).execute()


class GoogleAccessError(Exception):
    """
    error used in google_query. Should be deleted along with google_query
    """
    def __init__(self, *error_args):
        Exception.__init__(self, "Bad response status {}".format(error_args))
