import yaml

data = {
    'list': ['first_element', 2, 'три'],
    'number': 1240,
    'dict': {
        'euro': '€',
        'dollar': '$'
    }
}

with open('file.yaml', 'w', encoding='utf-8') as fy:
    yaml.dump(data, fy, allow_unicode=True, sort_keys=False)

with open('file.yaml', encoding='utf-8') as fy:
    print(fy.read())
