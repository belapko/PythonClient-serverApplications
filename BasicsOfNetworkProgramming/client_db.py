from sqlalchemy import create_engine, Table, Column, Integer, String, Text, MetaData, DateTime
from sqlalchemy.orm import mapper, sessionmaker
from common.variables import CLIENT_DATABASE, CLIENT_TEST_DATABASE
from datetime import datetime


class ClientStorage:
    class Users:
        def __init__(self, username):
            self.id = None
            self.name = username

    class MessagesHistory:
        def __init__(self, from_user, to_user, message):
            self.id = None
            self.from_user = from_user
            self.to_user = to_user
            self.message = message
            self.time = datetime.now()

    class Contacts:
        def __init__(self, username):
            self.id = None
            self.name = username

    def __init__(self, name):
        if __name__ == '__main__':
            self.db_engine = create_engine(CLIENT_TEST_DATABASE, echo=False, pool_recycle=7200,
                                           connect_args={'check_same_thread': False})
        else:
            self.db_engine = create_engine(CLIENT_DATABASE, echo=False, pool_recycle=7200,
                                           connect_args={'check_same_thread': False})

        self.metadata = MetaData()
        users = Table('Users', self.metadata,
                      Column('id', Integer, primary_key=True),
                      Column('name', String)
                      )
        messages_history = Table('Messages_History', self.metadata,
                                 Column('id', Integer, primary_key=True),
                                 Column('from_user', String),
                                 Column('to_user', String),
                                 Column('message', Text),
                                 Column('time', DateTime)
                                 )
        contacts = Table('Contacts', self.metadata,
                         Column('id', Integer, primary_key=True),
                         Column('name', String, unique=True)
                         )

        self.metadata.create_all(self.db_engine)

        mapper(self.Users, users)
        mapper(self.MessagesHistory, messages_history)
        mapper(self.Contacts, contacts)

        session = sessionmaker(bind=self.db_engine)
        self.session = session()

        self.session.query(self.Contacts).delete()
        self.session.commit()

    def add_contact(self, username):
        if not self.session.query(self.Contacts).filter_by(name=username).count():
            contact = self.Contacts(username)
            self.session.add(contact)
            self.session.commit()

    def del_contact(self, username):
        self.session.query(self.Contacts).filter_by(name=username).delete()
        self.session.commit()

    def add_users(self, users_list):
        self.session.query(self.Users).delete()
        for user in users_list:
            users = self.Users(user)
            self.session.add(users)
        self.session.commit()

    def save_message(self, from_user, to_user, message):
        msg = self.MessagesHistory(from_user, to_user, message)
        self.session.add(msg)
        self.session.commit()

    def get_contacts(self):
        return [name[0] for name in self.session.query(self.Contacts.name).all()]

    def get_users(self):
        return [name[0] for name in self.session.query(self.Users.name).all()]

    def is_known_user(self, username):
        if self.session.query(self.Users).filter_by(name=username).count():
            return True
        else:
            return False

    def is_known_contact(self, username):
        if self.session.query(self.Contacts).filter_by(name=username).count():
            return True
        else:
            return False

    def get_history(self, from_user=None, to_user=None):
        query = self.session.query(self.MessagesHistory)
        if from_user:
            query = query.filter_by(from_user=from_user)
        if to_user:
            query = query.filter_by(to_user=to_user)
        return [(history.from_user, history.to_user, history.message, history.time) for history in query.all()]


if __name__ == '__main__':
    test_db = ClientStorage('test1')
    for i in ['test3', 'test4', 'test5']:
        test_db.add_contact(i)
    test_db.add_contact('test4')
    test_db.add_users(['test1', 'test2', 'test3', 'test4', 'test5'])
    test_db.save_message('test1', 'test2', f'test_msg from {datetime.now()}')
    test_db.save_message('test2', 'test1', f'test_msg from {datetime.now()}')

    print(test_db.get_contacts())
    print('-' * 20)
    print(test_db.get_users())
    print('-' * 20)
    print(test_db.is_known_user('test1'))
    print(test_db.is_known_user('unknown1'))
    print('-' * 20)
    print(test_db.get_history('test2'))
    print(test_db.get_history(to_user='test2'))
    print('-' * 20)
    test_db.del_contact('test4')
    print(test_db.get_contacts())
