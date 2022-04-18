def can_be_in_byte(word):
    try:
        eval(f"b'{word}'")
    except SyntaxError:
        return f'word {word} can not be written in byte form'
    return f'word {word} can be written in byte form'

words = ['attribute', 'класс', 'функция', 'type']
for i in words:
    print(can_be_in_byte(i))

