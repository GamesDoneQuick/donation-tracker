from django.shortcuts import render
from tracker.models import Event

def index(request):
	return render(request, 'tracker_ui/index.html', dictionary={'event': Event.objects.latest(), 'events': Event.objects.all()})
