from django import forms
import tracker.widgets;

class DonationBidField(forms.fields.MultiValueField):
  widget = tracker.widgets.MegaFilterWidget(model='bidtarget');
  def __init__(self, *args, **kwargs):
    fields = (forms.fields.IntegerField(),);
    super(DonationBidField, self).__init__(fields, *args, **kwargs);
  
  def compress(self, data_list):
    return data_list;
  