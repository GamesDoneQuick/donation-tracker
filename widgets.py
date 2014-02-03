from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape, format_html, format_html_join
from tracker import models
import paypal
import re
from decimal import *
from django.forms import formsets;

class MegaFilterWidget(forms.widgets.MultiWidget):
  def __init__(self, model, attrs=None, **kwargs):
    self.model = model;
    widgets = (
      forms.widgets.HiddenInput(attrs={'class': 'mf_selection'}),
      forms.widgets.Select(attrs={'class': 'mf_grouping'}),
      forms.widgets.TextInput(attrs={'class': 'mf_filter'}), 
      forms.widgets.Select(attrs={'size': 6, 'class': 'mf_selectbox'}), 
    );
    super(MegaFilterWidget, self).__init__(widgets, attrs);
    
  def decompress(self, value):
    if value is not None:
      return [value[0], None, None, None];
    else:
      return [None]*4;
    
  def format_output(self, rendered_widgets):
    return format_html('<div class="mf_widget mf_model_{0}"> {1} <label class="mf_groupingLabel">Group:</label> {2} <label class="mf_filterLabel">Filter:</label> {3} <br /> {4} <br /> <span class="mf_description" /> </div>',
                        self.model, 
                        rendered_widgets[0],
                        rendered_widgets[1],
                        rendered_widgets[2],
                        rendered_widgets[3]);
