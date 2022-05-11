import sys
import os
import unittest
import json

sys.path.insert(0, os.path.join(os.getcwd(), '..'))

from common.variables import RESPONSE, ERROR, USER, ACCOUNT_NAME, TIME, ACTION, PRESENCE, ENCODING
from common.utils import send_message, get_message


class TestSocket:
    def __init__(self, test_dict):
        self.test_dict = test_dict
        self.encoded_message = None
        self.received_message = None

    def send(self, message_to_send):
        json_message = json.dumps(self.test_dict)
        self.encoded_message = json_message.encode(ENCODING)
        self.received_message = message_to_send

    def recv(self, max_len):
        json_message = json.dumps(self.test_dict)
        return json_message.encode(ENCODING)


class TestUtils(unittest.TestCase):
    test_dict = {
        ACTION: PRESENCE,
        TIME: 111111.111111,
        USER: {
            ACCOUNT_NAME: 'test_user'
        }
    }
    test_dict_recv_ok = {
        RESPONSE: 200
    }
    test_dict_recv_error = {
        RESPONSE: 400,
        ERROR: 'Bad request'
    }

    def test_send_message_ok(self):
        test_socket = TestSocket(self.test_dict)
        send_message(test_socket, self.test_dict)
        self.assertEqual(test_socket.encoded_message, test_socket.received_message)

    def test_send_message_error(self):
        test_socket = TestSocket(self.test_dict)
        send_message(test_socket, self.test_dict)
        self.assertRaises(TypeError, send_message, test_socket, 'wrong_dict')

    def test_get_message_ok(self):
        test_sock_ok = TestSocket(self.test_dict_recv_ok)
        self.assertEqual(get_message(test_sock_ok), self.test_dict_recv_ok)

    def test_get_message_error(self):
        test_sock_error = TestSocket(self.test_dict_recv_error)
        self.assertEqual(get_message(test_sock_error), self.test_dict_recv_error)


if __name__ == '__main__':
    unittest.main()
