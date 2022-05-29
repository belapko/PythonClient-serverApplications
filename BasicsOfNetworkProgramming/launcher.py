"""Лаунчер"""

import subprocess

PROCESS = []

while True:
    ACTION = input('Выберите действие: q - выход, '
                   's - запустить сервер и клиенты, x - закрыть все окна: ')

    if ACTION == 'q':
        break
    elif ACTION == 's':
        PROCESS.append(subprocess.Popen(['python server.py'], shell=True))
        for i in range(2):
            PROCESS.append(subprocess.Popen(['python client.py -m send'], shell=True))
        for i in range(5):
            PROCESS.append(subprocess.Popen(['python client.py -m listen'], shell=True))
    elif ACTION == 'x':
        while PROCESS:
            VICTIM = PROCESS.pop()
            VICTIM.kill()