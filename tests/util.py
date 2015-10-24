
def parse_test_mail(mail):
    lines = list(map(lambda x: x.partition(':'), filter(
        lambda x: x, map(lambda x: x.strip(), mail.message.split("\n")))))
    result = {}
    for line in lines:
        if line[2]:
            name = line[0].lower()
            value = line[2]
            if name not in result:
                result[name] = []
            result[name].append(value)
    return result
