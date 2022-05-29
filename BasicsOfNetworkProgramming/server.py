import argparse
import select
import sys
import json
import socket
import time

from common.variables import USER, ACTION, ACCOUNT_NAME, RESPONSE, MAX_CONNECTIONS, PRESENCE, TIME, ERROR, DEFAULT_PORT, \
    MESSAGE, MESSAGE_TEXT, SENDER
from common.utils import get_message, send_message
import logging
from logs import config_server_log
from log_decorator import log

SERVER_LOGGER = logging.getLogger('server')


@log
def process_client_message(message, messages_list, client):
    # Принимает словарь - сообщение от клиента, проверяет корректность, возвращает словарь - ответ
    SERVER_LOGGER.debug(f'Сообщение от клиента: {message}')
    if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
            and USER in message and message[USER][ACCOUNT_NAME] == 'Guest':
        send_message(client, {RESPONSE: 200})
        return
        # Если это сообщение, то добавляем его в очередь сообщений. Ответ не требуется.
    elif ACTION in message and message[ACTION] == MESSAGE and \
            TIME in message and MESSAGE_TEXT in message:
        messages_list.append((message[ACCOUNT_NAME], message[MESSAGE_TEXT]))
        return
        # Иначе отдаём Bad request
    else:
        send_message(client, {
            RESPONSE: 400,
            ERROR: 'Bad Request'
        })
        return


@log
def arg_parser():
    """Парсер аргументов коммандной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-a', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    # проверка получения корретного номера порта для работы сервера.
    if not 1023 < listen_port < 65536:
        SERVER_LOGGER.critical(
            f'Попытка запуска сервера с указанием неподходящего порта '
            f'{listen_port}. Допустимы адреса с 1024 до 65535.')
        sys.exit(1)

    return listen_address, listen_port


def main():
    # Загрузка параметров командной строки. Нет параметров - задаем значения по умолчанию.
    # Сначала обрабатываем порт
    # try:
    #     if '-p' in sys.argv:
    #         listen_port = int(sys.argv[sys.argv.index('-p') + 1])
    #     else:
    #         listen_port = DEFAULT_PORT
    #     if listen_port < 1024 or listen_port > 65535:
    #         SERVER_LOGGER.critical(f'Неподходящий номер порта: {listen_port}')
    #         raise ValueError
    # except IndexError:
    #     print('После параметра -\'p\' необходимо указать номер порта.')
    #     sys.exit(1)
    # except ValueError:
    #     print('Номер порта может быть указан только в диапазоне от 1024 до 65535.')
    #     sys.exit(1)
    #
    # # Загружаем какой адрес слушать
    # try:
    #     if '-a' in sys.argv:
    #         listen_address = sys.argv[sys.argv.index('-a') + 1]
    #     else:
    #         listen_address = ''
    #
    # except IndexError:
    #     print('После параметра \'a\' необходимо указать адрес, который будет слушать сервер.')
    #     sys.exit(1)
    # SERVER_LOGGER.info(f'Запущен сервер с параметрами {listen_address}, {listen_port}')

    listen_address, listen_port = arg_parser()
    # Готовим сокет
    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Создание сокета
    transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Может слушать несколько приложений
    transport.bind((listen_address, listen_port))  # Связь сокета с хостом и портом
    transport.settimeout(0.5)

    clients_list = []
    messages_queue = []

    transport.listen(MAX_CONNECTIONS)  # Максимальное кол-во подключений в очереди
    while True:
        try:
            client, client_address = transport.accept()  # Принять подключение. Возвращает кортеж: новый сокет, адрес клиента
        except OSError:
            pass
        else:
            SERVER_LOGGER.info(f'Соединено с клиентом {client_address}')
            clients_list.append(client)

        data_to_send = []
        data_to_receive = []
        errors_list = []
        try:
            if clients_list:
                data_to_receive, data_to_send, errors_list = select.select(clients_list, clients_list, [], 0)
        except OSError:
            pass

        if data_to_receive:
            for client_with_message in data_to_receive:
                try:
                    process_client_message(get_message(client_with_message), messages_queue, client_with_message)
                except:
                    SERVER_LOGGER.info(
                        f'клиент {client_with_message.getpeername()} был отключён')
                    # getpeername Return the remote address to which the socket is connected.
                    clients_list.remove(client_with_message)

        if messages_queue and data_to_send:
            message = {
                ACTION: MESSAGE,
                SENDER: messages_queue[0][0],
                TIME: time.time(),
                MESSAGE_TEXT: messages_queue[0][1]
            }
            del messages_queue[0]
            for waiting_client in data_to_send:
                try:
                    send_message(waiting_client, message)
                except:
                    SERVER_LOGGER.info(f'клиент {waiting_client.getpeername()} был отключён')
                    waiting_client.close()
                    clients_list.remove(waiting_client)

        #
        # try:
        #     message_from_client = get_message(client)
        #     SERVER_LOGGER.debug(f'Получено сообщение: {message_from_client}')
        #     print(message_from_client)
        #     response = process_client_message(message_from_client)
        #     SERVER_LOGGER.debug(f'Сформирован ответ клиенту: {response}')
        #     send_message(client, response)
        #     SERVER_LOGGER.debug(f'Соединение с {client_address} закрывается')
        #     client.close()
        # except (ValueError, json.JSONDecodeError):
        #     SERVER_LOGGER.error(f'Некорректное сообщение от клиента {client_address}')
        #     print('Некорректное сообщение от клиента')
        #     client.close()


if __name__ == '__main__':
    main()
