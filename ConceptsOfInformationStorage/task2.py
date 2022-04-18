def to_bytes(word):
    return eval(f"b'{word}'")

lst = ['class', 'function', 'method']
for i in lst:
    print(f'содержание переменной: {to_bytes(i)}')
    print(f'тип переменной: {type(to_bytes(i))}')
    print(f'длина переменной: {len(to_bytes(i))}')
    print('----------------------')
