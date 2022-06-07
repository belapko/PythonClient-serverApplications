import tabulate
from host_range_ping_2 import host_range_ping

def host_range_ping_tab():
    result = host_range_ping()
    print()
    print(tabulate.tabulate([result], headers='keys', tablefmt='pipe', stralign='center'))

if __name__ == '__main__':
    host_range_ping_tab()