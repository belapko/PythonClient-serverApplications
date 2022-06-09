import ipaddress

from host_ping_1 import host_ping


def host_range_ping():
    ipv4 = ipaddress.ip_address(input('Введите адрес для проверки: '))
    last_oct = int(str(ipv4).split('.')[-1])
    while True:
        ip_num = input('Введите кол-во адресов: ')
        if last_oct + int(ip_num) > 255 + 1:
            print(f'Максимальное число хостов {255 + 1 - last_oct}')
        else:
            break
    addresses_list = []
    for i in range(int(ip_num)):
        addresses_list.append(str(ipv4 + i))
    host_ping(addresses_list, 1)


if __name__ == "__main__":
    host_range_ping()
