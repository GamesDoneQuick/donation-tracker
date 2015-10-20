from django.core.exceptions import ValidationError

__all__ = [
	'positive',
	'nonzero',
]

def positive(value):
  if value <  0: raise ValidationError('Value cannot be negative')

def nonzero(value):
  if value == 0: raise ValidationError('Value cannot be zero') 

