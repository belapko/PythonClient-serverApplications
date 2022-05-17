import sys
import json
import socket
from common.variables import USER, ACTION, ACCOUNT_NAME, RESPONSE, MAX_CONNECTIONS, PRESENCE, TIME, ERROR, DEFAULT_PORT
from common.utils import get_message, send_message
import logging
from logs import config_server_log
from log_decorator import log

SERVER_LOGGER = logging.getLogger('server')

@log
def process_client_message(message):
    # Принимает словарь - сообщение от клиента, проверяет корректность, возвращает словарь - ответ
    SERVER_LOGGER.debug(f'Сообщение от клиента: {message}')
    if ACTION in message and message[ACTION] == PRESENCE and TIME in message and USER in message \
            and message[USER][ACCOUNT_NAME] == 'Guest':
        return {RESPONSE: 200}
    return {
        RESPONSE: 400,
        ERROR: 'Bad request'
    }


def main():
    # Загрузка параметров командной строки. Нет параметров - задаем значения по умолчанию.
    # Сначала обрабатываем порт
    try:
        if '-p' in sys.argv:
            listen_port = int(sys.argv[sys.argv.index('-p') + 1])
        else:
            listen_port = DEFAULT_PORT
        if listen_port < 1024 or listen_port > 65535:
            SERVER_LOGGER.critical(f'Неподходящий номер порта: {listen_port}')
            raise ValueError
    except IndexError:
        print('После параметра -\'p\' необходимо указать номер порта.')
        sys.exit(1)
    except ValueError:
        print('Номер порта может быть указан только в диапазоне от 1024 до 65535.')
        sys.exit(1)

    # Загружаем какой адрес слушать
    try:
        if '-a' in sys.argv:
            listen_address = sys.argv[sys.argv.index('-a') + 1]
        else:
            listen_address = ''

    except IndexError:
        print('После параметра \'a\' необходимо указать адрес, который будет слушать сервер.')
        sys.exit(1)
    SERVER_LOGGER.info(f'Запущен сервер с параметрами {listen_address}, {listen_port}')

    # Готовим сокет
    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Создание сокета
    transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Может слушать несколько приложений
    transport.bind((listen_address, listen_port))  # Связь сокета с хостом и портом

    transport.listen(MAX_CONNECTIONS)  # Максимальное кол-во подключений в очереди
    while True:
        client, client_address = transport.accept()  # Принять подключение. Возвращает кортеж: новый сокет, адрес клиента
        try:
            message_from_client = get_message(client)
            SERVER_LOGGER.debug(f'Получено сообщение: {message_from_client}')
            print(message_from_client)
            response = process_client_message(message_from_client)
            SERVER_LOGGER.debug(f'Сформирован ответ клиенту: {response}')
            send_message(client, response)
            SERVER_LOGGER.debug(f'Соединение с {client_address} закрывается')
            client.close()
        except (ValueError, json.JSONDecodeError):
            SERVER_LOGGER.error(f'Некорректное сообщение от клиента {client_address}')
            print('Некорректное сообщение от клиента')
            client.close()


if __name__ == '__main__':
    main()
