import json


def write_order_to_json(item, quantity, price, buyer, date):
    with open('orders.json', 'r', encoding='utf-8') as oj:
        data = json.load(oj)
        data['orders'].append({
            'item': item,
            'quantity': quantity,
            'price': price,
            'buyer': buyer,
            'date': date
        })
    with open('orders.json', 'w', encoding='utf-8') as oj:
        json.dump(data, oj, indent=4, ensure_ascii=False)


write_order_to_json('computer', 3, 6900, 'Stepan', '04/12/2021')
write_order_to_json('monitor', 2, 12390, 'Степан', '31/12/2021')
