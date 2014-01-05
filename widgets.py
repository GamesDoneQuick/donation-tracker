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

class DonationBidWidget(forms.widgets.MultiWidget):
  def __init__(self, attrs=None, **kwargs):
    widgets = (
      forms.widgets.HiddenInput(attrs={'class': 'cdonationbidid'}),
      forms.widgets.Select(attrs={'class': 'cdonationbidtype'}),
      forms.widgets.TextInput(attrs={'class': 'cdonationbidfilter'}), 
      forms.widgets.Select(attrs={'size': 6, 'class': 'cdonationbidselect'}), 
    );
    super(DonationBidWidget, self).__init__(widgets, attrs);
    
  def decompress(self, value):
    if value is not None:
      return [value[0], None, None, None];
    else:
      return [None]*4;
    
  def format_output(self, rendered_widgets):
    return format_html('<div class="cdonationbidwidget"> {0} <label>Group:</label> {1} <label>Filter:</label> {2} <br /> {3} <br /> <span class="cdonationbiddesc" /> </div>',
                        rendered_widgets[0],
                        rendered_widgets[1],
                        rendered_widgets[2],
                        rendered_widgets[3]);
