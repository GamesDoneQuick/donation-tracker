import django.dispatch

model_created = django.dispatch.Signal(providing_args=['instance'])
model_changed = django.dispatch.Signal(providing_args=['instance', 'fields'])
model_deleted = django.dispatch.Signal(providing_args=['instance'])
model_reordered = django.dispatch.Signal(providing_args=['instance', 'ordinals'])
