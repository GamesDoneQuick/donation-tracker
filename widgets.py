from django import forms
from django.utils.html import format_html


class MegaFilterWidget(forms.widgets.Widget):
    def __init__(self, model, **kwargs):
        self.model = model
        super(MegaFilterWidget, self).__init__(**kwargs)

    def value_from_datadict(self, data, files, name):
        if name in data and data[name] and data[name] != 'None':
            return int(data[name])
        else:
            return None

    def render(self, name, value, attrs=None):
        return format_html("""
    <div class="mf_widget mf_model_{0}">
    <input id="id_{1}" name="{1}" class="mf_selection" type="hidden" value="{2}"/>
    <label class="mf_groupingLabel">Group:</label> <select class="mf_grouping"></select>
    <label class="mf_filterLabel">Filter:</label> <input class="mf_filter" type="text"/> <br />
    <select size="6" class="mf_selectbox"></select> <br />
    <span class="mf_description" /> </div>""", self.model, name, value)


class NumberInput(forms.widgets.Input):
    def __init__(self, attrs=None):
        self.input_type = "number"
        super(NumberInput, self).__init__(attrs)


class ReadOnlyWidget(forms.widgets.Widget):
    def render(self, _, value, attrs={}):
        return value
