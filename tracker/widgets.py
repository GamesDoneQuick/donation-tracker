from django import forms


# TODO: is this still needed?
class NumberInput(forms.widgets.Input):
    def __init__(self, attrs=None):
        self.input_type = 'number'
        super(NumberInput, self).__init__(attrs)
