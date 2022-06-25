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

    # Класс - отображение таблицы контактов пользователей
    class UsersContacts:
        def __init__(self, user, contact):
            self.id = None
            self.user = user
            self.contact = contact

    # Класс отображение таблицы истории действий
    class UsersHistory:
        def __init__(self, user):
            self.id = None
            self.user = user
            self.sent = 0
            self.accepted = 0

    def __init__(self, path=None):
        if __name__ == '__main__':
            self.db_engine = create_engine(SERVER_TEST_DATABASE, echo=True, pool_recycle=7200,
                                           connect_args={'check_same_thread': False})
        else:
            self.db_engine = create_engine(f'sqlite:///{path}', echo=False, pool_recycle=7200,
                                           connect_args={'check_same_thread': False})
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
        # Создаём таблицу контактов пользователей
        contacts = Table('Contacts', self.metadata,
                         Column('id', Integer, primary_key=True),
                         Column('user', ForeignKey('Users.id')),
                         Column('contact', ForeignKey('Users.id'))
                         )

        # Создаём таблицу истории пользователей
        users_history_table = Table('History', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('user', ForeignKey('Users.id')),
                                    Column('sent', Integer),
                                    Column('accepted', Integer)
                                    )
        self.metadata.create_all(self.db_engine)

        mapper(self.AllUsers, users_table)
        mapper(self.ActiveUsers, active_users_table)
        mapper(self.LoginHistory, users_login_history)
        mapper(self.UsersContacts, contacts)
        mapper(self.UsersHistory, users_history_table)

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

    def process_message(self, sender, recipient):
        # Получаем ID отправителя и получателя
        sender = self.session.query(self.AllUsers).filter_by(name=sender).first().id
        recipient = self.session.query(self.AllUsers).filter_by(name=recipient).first().id
        # Запрашиваем строки из истории и увеличиваем счётчики
        sender_row = self.session.query(self.UsersHistory).filter_by(user=sender).first()
        sender_row.sent += 1
        recipient_row = self.session.query(self.UsersHistory).filter_by(user=recipient).first()
        recipient_row.accepted += 1

        self.session.commit()

    def add_contact(self, user, contact):
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        # Проверяем что не дубль и что контакт может существовать (полю пользователь мы доверяем)
        if not contact or self.session.query(self.UsersContacts).filter_by(user=user.id, contact=contact.id).count():
            return

        # Создаём объект и заносим его в базу
        contact_row = self.UsersContacts(user.id, contact.id)
        self.session.add(contact_row)
        self.session.commit()

    def remove_contact(self, user, contact):
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        # Проверяем что контакт может существовать (полю пользователь мы доверяем)
        if not contact:
            return

        # Удаляем требуемое
        print(self.session.query(self.UsersContacts).filter(
            self.UsersContacts.user == user.id,
            self.UsersContacts.contact == contact.id
        ).delete())
        self.session.commit()

    def get_contacts(self, username):
        # Запрашиваем указанного пользователя
        user = self.session.query(self.AllUsers).filter_by(name=username).one()

        # Запрашиваем его список контактов
        query = self.session.query(self.UsersContacts, self.AllUsers.name). \
            filter_by(user=user.id). \
            join(self.AllUsers, self.UsersContacts.contact == self.AllUsers.id)

        # выбираем только имена пользователей и возвращаем их.
        return [contact[1] for contact in query.all()]

    # Функция возвращает количество переданных и полученных сообщений
    def message_history(self):
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login,
            self.UsersHistory.sent,
            self.UsersHistory.accepted
        ).join(self.AllUsers)
        # Возвращаем список кортежей
        return query.all()


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
