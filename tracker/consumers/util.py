import decimal

from django.core.serializers.json import DjangoJSONEncoder


class DecimalFloatEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        else:
            return super().default(o)
