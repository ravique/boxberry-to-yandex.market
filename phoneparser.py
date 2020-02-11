from errors import PointParseError


def parse_phone(raw_phone: str):
    phone = list(raw_phone)
    trim = (')', '(', '-', ' ')
    for symbol in trim:
        while symbol in phone:
            phone.remove(symbol)

    if phone[0] != '+':
        if phone[0] == '8':
            phone[0] = '7'
        phone = ['+'] + phone

    if len(phone) != 12:
        raise PointParseError('invalid phone: {}'.format(raw_phone))

    phone = ''.join(phone)

    return '{} ({}) {}-{}-{}'.format(phone[:2], phone[2:5], phone[5:8], phone[8:10], phone[10:12])

