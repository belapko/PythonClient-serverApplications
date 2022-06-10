import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.getcwd(), '..'))

from server import Server
from common.variables import RESPONSE, TIME, ACTION, PRESENCE, USER, ACCOUNT_NAME, ERROR

class TestServer(unittest.TestCase):
    correct_dict = {
        ACTION: PRESENCE,
        TIME: 111111.111111,
        USER: {
            ACCOUNT_NAME: 'Guest'
        }
    }

    dict_without_action = {
        TIME: 111111.111111,
        USER: {
            ACCOUNT_NAME: 'Guest'
        }
    }

    test_dict_recv_ok = {
        RESPONSE: 200
    }
    test_dict_recv_error = {
        RESPONSE: 400,
        ERROR: 'Bad request'
    }

    def test_correct(self):
        self.assertEqual(Server.process_client_message(self.correct_dict), self.test_dict_recv_ok)

    def test_without_action(self):
        self.assertEqual(Server.process_client_message(self.dict_without_action), self.test_dict_recv_error)




if __name__ == '__main__':
    unittest.main()
