import argparse
import select
import sys
import socket
from common.variables import USER, ACTION, ACCOUNT_NAME, PRESENCE, TIME, ERROR, DEFAULT_PORT, MESSAGE, MESSAGE_TEXT, \
    SENDER, DESTINATION, RESPONSE_200, RESPONSE_400, EXIT
from common.utils import get_message, send_message
import logging
from log_decorator import log

SERVER_LOGGER = logging.getLogger('server')


@log
def arg_parser():
    """Парсер аргументов командной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-a', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    return listen_address, listen_port


class Server:
    def __init__(self, listen_address, listen_port):
        self.sock = None
        self.addr = listen_address
        self.port = listen_port
        self.clients = []  # Список подключенных клиентов
        self.messages = []
        self.names = dict()  # {client_name: client_socket}

    def init_socket(self):
        SERVER_LOGGER.info(f'Порт для подключения к серверу: {self.port}\nАдрес сервера: {self.addr}')

        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.bind((self.addr, self.port))
        transport.settimeout(0.5)

        self.sock = transport
        self.sock.listen()

    def main_loop(self):
        self.init_socket()

        while True:
            # Ждём подключения, если таймаут вышел, ловим исключение.
            try:
                client, client_address = self.sock.accept()
            except OSError:
                pass
            else:
                SERVER_LOGGER.info(f'Установлено соединение с клиентом: {client_address}')
                self.clients.append(client)

            data_to_receive = []
            data_to_send = []
            errors_lst = []
            # Проверяем на наличие ждущих клиентов
            try:
                if self.clients:
                    data_to_receive, data_to_send, errors_lst = select.select(self.clients, self.clients, [], 0)
            except OSError:
                pass
            # принимаем сообщения и если ошибка, исключаем клиента
            if data_to_receive:
                SERVER_LOGGER.info(f'data_to_receive: {data_to_receive}')
                for client_with_message in data_to_receive:
                    try:
                        self.process_client_message(get_message(client_with_message), client_with_message)
                    except Exception as e:
                        SERVER_LOGGER.info(f'Клиент {client_with_message.getpeername()} отключился. Ошибка {e}')
                        self.clients.remove(client_with_message)

            for message in self.messages:
                try:
                    self.process_message(message, data_to_send)
                except Exception as e:
                    SERVER_LOGGER.info(f'Связь с клиентом {message[DESTINATION]} была потеряна. Ошибка {e}')
                    self.clients.remove(self.names[message[DESTINATION]])
                    del self.names[message[DESTINATION]]
            self.messages.clear()

    # Функция адресной отправки сообщения определённому клиенту
    def process_message(self, message, listen_socks):
        if message[DESTINATION] in self.names and self.names[message[DESTINATION]] in listen_socks:
            send_message(self.names[message[DESTINATION]], message)
            SERVER_LOGGER.info(f'Отправлено сообщение пользователю: {message[DESTINATION]} от: {message[SENDER]}')
        elif message[DESTINATION] in self.names and self.names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            SERVER_LOGGER.info(f'Пользователя {message[DESTINATION]} не существует. Отправка невозможна.')

    def process_client_message(self, message, client):
        SERVER_LOGGER.debug(f'Разбор сообщения: {message} от клиента')
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message and USER in message:
            # Регистрация пользователя, если такого ещё не существует
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                send_message(client, RESPONSE_200)
            # Пользователь уже существует - отправляем ответ и завершаем соединение
            else:
                response = RESPONSE_400
                response[ERROR] = f'Такое имя уже занято.'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return
        # Если пользователь отправил какое-то сообщение, то добавляем в очередь сообщений
        elif ACTION in message and message[ACTION] == MESSAGE \
                and DESTINATION in message and TIME in message and SENDER in message and MESSAGE_TEXT in message:
            SERVER_LOGGER.info(f'Сообщение добавлено в очередь')
            self.messages.append(message)
            return
        # Если клиент хочет выйти, удаляем его из списка клиентов и закрываем соединение
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.clients.remove(self.names[ACCOUNT_NAME])
            self.names[ACCOUNT_NAME].close()
            del self.names[ACCOUNT_NAME]
            SERVER_LOGGER.info(f'Клиент {self.names[ACCOUNT_NAME]} вышел.')
            return
        # Если всё плохо и непонятно - Bad request
        else:
            response = RESPONSE_400
            response[ERROR] = f'Неверный запрос.'
            send_message(client, response)
            return


def main():
    listen_address, listen_port = arg_parser()
    server = Server(listen_address, listen_port)
    server.main_loop()


if __name__ == '__main__':
    main()
