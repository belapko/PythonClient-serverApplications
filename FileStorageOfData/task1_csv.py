import csv
import os
import re

import chardet


def get_data():
    dir_with_files = os.path.join(os.path.abspath('files_for_csv'))
    files = os.listdir(dir_with_files)
    result = []
    detector = chardet.UniversalDetector()
    for file in files:
        with open(f'{dir_with_files}/{file}', 'rb') as fl:
            for line in fl:
                detector.feed(line)
                if detector.done:
                    break
            detector.close()
        with open(f'{dir_with_files}/{file}', encoding=detector.result['encoding']) as fl:
            for line in fl:
                result += re.findall(r'^(Изготовитель системы|Название ОС|Код продукта|Тип системы).*:\s+([^:\n]+)\s*$',
                                     line)

    os_prod_list, os_name_list, os_code_list, os_type_list = [], [], [], []
    main_data = [['Изготовитель системы', 'Название ОС', 'Код продукта', 'Тип системы']]
    for item in result:
        os_prod_list.append(item[1]) if item[0] == main_data[0][0] else None
        os_name_list.append(item[1]) if item[0] == main_data[0][1] else None
        os_code_list.append(item[1]) if item[0] == main_data[0][2] else None
        os_type_list.append(item[1]) if item[0] == main_data[0][3] else None

    for i in range(len(os_prod_list)):
        main_data.append([os_prod_list[i], os_name_list[i], os_code_list[i], os_type_list[i]])

    return main_data


link_to_csv = os.path.abspath('info.csv')


def write_to_csv(link):
    data = get_data()
    with open(link, 'w', encoding='utf-8') as cf:
        cf_writer = csv.writer(cf)
        cf_writer.writerows(data)


write_to_csv(link_to_csv)
