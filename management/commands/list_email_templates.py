from django.core.management.base import BaseCommand, CommandError

import post_office.models
import tracker.commandutil as commandutil

class Command(commandutil.TrackerCommand):
    help = 'List all e-mail templates'

    def add_arguments(self, parser):
        parser.add_argument('-f', '--filter', help='filter by name', default='')

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        templateList = post_office.models.EmailTemplate.objects.all()
        
        if 'filter' in options:
            templateList = templateList.filter(name__icontains=options['filter'])

        if templateList.exists():
            for template in templateList:
                self.message('{0}'.format(template.name), 0)
        else:
            self.message("No templates found.")

