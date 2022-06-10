import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.getcwd(), '..'))

from client import create_presence, process_response_answer
from common.variables import RESPONSE, TIME, ACTION, PRESENCE, USER, ACCOUNT_NAME, ERROR


class TestClient(unittest.TestCase):
    correct_dict = {
        ACTION: PRESENCE,
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

    def test_presence_ok(self):
        test_presence = create_presence()
        test_presence[TIME] = 111111.111111
        self.assertEqual(test_presence, self.correct_dict)

    def test_ans_200(self):
        self.assertEqual(process_ans(self.test_dict_recv_ok), '200 : OK')

    def test_ans_400(self):
        self.assertEqual(process_ans(self.test_dict_recv_error), '400 : Bad request')

if __name__ == '__main__':
    unittest.main()
