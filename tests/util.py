def parse_test_mail(mail):
    lines = list(
        [
            x.partition(":")
            for x in [x for x in [x.strip() for x in mail.message.split("\n")] if x]
        ]
    )
    result = {}
    for line in lines:
        if line[2]:
            name = line[0].lower()
            value = line[2]
            if name not in result:
                result[name] = []
            result[name].append(value)
    return result
