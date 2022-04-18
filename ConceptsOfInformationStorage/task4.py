words = ['разработка', 'администрирование', 'protocol', 'standard']
for i in words:
    encode_word = str.encode(i, encoding='utf-8')
    print(encode_word, type(encode_word))
    decode_word = bytes.decode(encode_word, encoding='utf-8')
    print(decode_word, type(decode_word))
    print('------------')