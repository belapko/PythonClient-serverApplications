import subprocess
import platform
import chardet


def ping(site):
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    args = ['ping', param, '2', site]
    result = subprocess.Popen(args, stdout=subprocess.PIPE)
    for line in result.stdout:
        result = chardet.detect(line)
        line = line.decode(result['encoding']).encode('utf-8')
        print(line.decode('utf-8'))

sites = ['yandex.ru', 'youtube.com']
for site in sites:
    ping(site)