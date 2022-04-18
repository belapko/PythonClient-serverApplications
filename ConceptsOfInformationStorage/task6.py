import chardet
detector = chardet.UniversalDetector()
for line in open('test_file.txt', 'rb'):
    # encoding = chardet.detect(line)['encoding']
    detector.feed(line)
print(detector.result)

file = open("test_file.txt", "r", encoding=detector.result['encoding'])
print(file.read())