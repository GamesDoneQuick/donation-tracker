from django.shortcuts import render
from tracker.models import Event
from django.views.decorators.csrf import csrf_protect

@csrf_protect
def index(request):
	return render(request, 'tracker_ui/index.html', dictionary={'event': Event.objects.latest(), 'events': Event.objects.all()})
