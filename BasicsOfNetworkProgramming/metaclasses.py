import dis


class ServerVerifier(type):
    def __init__(cls, name, bases, dct):
        methods = []
        attrs = []
        for func in dct:
            try:
                ret = dis.get_instructions(dct[func])
            except TypeError:
                pass
            else:
                for i in ret:
                    if i.opname == 'LOAD_GLOBAL' or i.opname == 'LOAD_METHOD':
                        if i.argval not in methods:
                            methods.append(i.argval)
                    elif i.opname == 'LOAD_ATTR':
                        if i.argval not in attrs:
                            attrs.append(i.argval)

        if 'connect' in methods:
            raise TypeError(f'Метод "connect" недопустим в серверном классе.')
        if 'SOCK_STREAM' not in attrs and 'AF_INET' not in attrs:
            raise TypeError(f'Некорректная инициализация сокета.')

        super().__init__(name, bases, dct)


class ClientVerifier(type):
    def __init__(cls, name, bases, dct):
        methods = []
        for func in dct:
            try:
                ret = dis.get_instructions(dct[func])
            except TypeError:
                pass
            else:
                for i in ret:
                    if i.opname == 'LOAD_GLOBAL' or i.opname == 'LOAD_METHOD':
                        if i.argval not in methods:
                            methods.append(i.argval)

        if 'accept' in methods or 'listen' in methods:
            raise TypeError(f'В классе {name} используются методы accept/listen')
        if 'get_message' in methods or 'send_message' in methods:
            pass
        else:
            raise TypeError(f'Отсутствует работа с сокетами')

        super().__init__(name, bases, dct)
