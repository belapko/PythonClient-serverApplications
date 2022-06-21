import time
from pprint import pprint
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime
from sqlalchemy.orm import mapper, sessionmaker
from common.variables import SERVER_TEST_DATABASE, SERVER_DATABASE
from datetime import datetime


class ServerStorage:
    class AllUsers:
        def __init__(self, username):
            self.name = username
            self.last_login = datetime.now()
            self.id = None

    class ActiveUsers:
        def __init__(self, user_id, ip_address, port, login_time):
            self.user = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time
            self.id = None

    class LoginHistory:
        def __init__(self, user_id, ip_address, port, login_time):
            self.user = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time
            self.id = None

    def __init__(self):
        if __name__ == '__main__':
            self.db_engine = create_engine(SERVER_TEST_DATABASE, echo=True, pool_recycle=7200)
        else:
            self.db_engine = create_engine(SERVER_DATABASE, echo=False, pool_recycle=7200)
        self.metadata = MetaData()
        users_table = Table('Users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('name', String, unique=True),
                            Column('last_login', DateTime)
                            )
        active_users_table = Table('Active_Users', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user', ForeignKey('Users.id'), unique=True),
                                   Column('ip_address', String),
                                   Column('port', Integer),
                                   Column('login_time', DateTime)
                                   )
        users_login_history = Table('Login_History', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('user', ForeignKey('Users.id')),
                                    Column('ip_address', String),
                                    Column('port', Integer),
                                    Column('login_time', DateTime)
                                    )
        self.metadata.create_all(self.db_engine)

        mapper(self.AllUsers, users_table)
        mapper(self.ActiveUsers, active_users_table)
        mapper(self.LoginHistory, users_login_history)

        session = sessionmaker(bind=self.db_engine)
        self.session = session()

        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    # Пользователь вошёл - записали в бд
    def user_login(self, username, ip_address, port):
        is_user = self.session.query(self.AllUsers).filter_by(name=username)
        if is_user.count():  # Пользователь есть в бд - перезаписали last_login
            user = is_user.first()
            user.last_login = datetime.now()
        else:  # creating new user in db
            user = self.AllUsers(username)
            self.session.add(user)
            self.session.commit()

        add_new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.now())
        self.session.add(add_new_active_user)

        add_to_history = self.LoginHistory(user.id, ip_address, port, datetime.now())
        self.session.add(add_to_history)

        self.session.commit()

    def user_logout(self, username):
        user = self.session.query(self.AllUsers).filter_by(name=username).first()
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()
        self.session.commit()

    def users_list(self):
        all_users = self.session.query(self.AllUsers.name, self.AllUsers.last_login)
        return all_users.all()

    def active_users_list(self):
        all_active_users = self.session.query(self.ActiveUsers.user, self.ActiveUsers.ip_address,
                                              self.ActiveUsers.port, self.ActiveUsers.login_time).join(self.AllUsers)
        return all_active_users.all()

    def login_history_list(self, username=None):
        history = self.session.query(self.AllUsers.name, self.LoginHistory.login_time, self.LoginHistory.ip_address,
                                     self.LoginHistory.port).join(self.AllUsers)
        if username:
            history = history.filter(self.AllUsers.name == username)
        return history.all()


if __name__ == '__main__':
    test_db = ServerStorage()
    test_db.user_login('client1', ip_address='192.168.1.1', port=8080)
    test_db.user_login('client2', ip_address='192.168.1.2', port=7070)

    print('active users: client1, client2')
    pprint(test_db.active_users_list())
    test_db.user_logout('client1')
    print('active users: client2')
    pprint(test_db.active_users_list())

    time.sleep(3)
    test_db.user_login('client1', ip_address='192.168.1.1', port=8080)

    print('login history')
    pprint(test_db.login_history_list())
    pprint(test_db.login_history_list('client1'))
    print('all users')
    pprint(test_db.users_list())
