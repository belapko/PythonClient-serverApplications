import platform
import threading
import ipaddress
import socket
import locale
import time
from subprocess import Popen, PIPE

encoding = locale.getpreferredencoding()

results = []


def host_ping(ip_address, ping_nums):
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    args = ['ping', param, str(ping_nums), str(ip_address)]
    response = Popen(args, stdout=PIPE, stdin=PIPE)
    if response.wait() == 0:
        results.append(f'Узел {str(ip_address)} доступен')
    else:
        results.append(f'Узел {str(ip_address)} не доступен')


def str_ip_to_ipv4(addresses_list):
    for i in range(len(addresses_list)):
        try:
            addresses_list[i] = str(ipaddress.ip_address(socket.gethostbyname(addresses_list[i])))
        except:
            addresses_list[i] = addresses_list[i]
    return addresses_list


def time_of_func(func):
    def wrapper(*args):
        start = time.time()
        result = func(*args)
        print(time.time() - start)
        return result

    return wrapper


@time_of_func
def threads(addresses_list):
    all_threads = []
    for ipv4 in addresses_list:
        thread = threading.Thread(target=host_ping, args=(ipv4, 5), daemon=True)
        thread.start()
        all_threads.append(thread)
    for every_thread in all_threads:
        every_thread.join()


@time_of_func
def ping_without_threads(lst):
    for ipaddr in lst:
        host_ping(ipaddr, 5)


if __name__ == '__main__':
    list_of_addresses = ['google.com', '192.168.0.1', 'ya.ru', '10.255.255.255', 'a']
    lst = str_ip_to_ipv4(list_of_addresses)
    threads(lst)
    print(results)
    print('-' * 50)
    ping_without_threads(lst)
