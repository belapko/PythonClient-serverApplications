import logging

DEFAULT_PORT = 7000
DEFAULT_IP_ADDRESS = '127.0.0.1'
MAX_CONNECTIONS = 5
MAX_PACKAGE_LENGTH = 1024
ENCODING = 'utf-8'
LOGGING_LEVEL = logging.DEBUG

ACTION = 'action'
TIME = 'time'
USER = 'user'
ACCOUNT_NAME = 'account_name'
SENDER = 'from'
DESTINATION = 'to'

PRESENCE = 'presence'
RESPONSE = 'response'
ERROR = 'error'
MESSAGE = 'message'
MESSAGE_TEXT = 'mess_text'
EXIT = 'exit'
GET_CONTACTS = 'get_contacts'
LIST_INFO = 'data_list'
REMOVE_CONTACT = 'remove'
ADD_CONTACT = 'add'
USERS_REQUEST = 'get_users'

RESPONSE_200 = {RESPONSE: 200}
RESPONSE_400 = {
    RESPONSE: 400,
    ERROR: None
}
RESPONSE_202 = {
    RESPONSE: 202,
    LIST_INFO: None
}

SERVER_DATABASE = 'sqlite:///server_db.db3'
SERVER_TEST_DATABASE = 'sqlite:///server_test_db.db3'

CLIENT_DATABASE = 'sqlite:///client_db.db3'
CLIENT_TEST_DATABASE = 'sqlite:///client_test_db.db3'
