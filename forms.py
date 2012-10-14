from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
import re

class UsernameForm(forms.Form):
	username = forms.CharField(
		max_length=255,
		widget=forms.TextInput(attrs={'class': 'required username'}))

	def clean_username(self):
		if 'username' in self.cleaned_data:
			username = self.cleaned_data['username']
			if not re.match(r'^[a-zA-Z0-9_]+$', username):
				raise forms.ValidationError(_("Usernames can only contain letters, numbers, and the underscore"))
			if username[:10]=='openiduser':
				raise forms.ValidationError(_("Username may not start with 'openiduser'"))
			if User.objects.filter(username=username).count() > 0:
				raise forms.ValidationError(_("Username already in use"))
			return self.cleaned_data['username']
