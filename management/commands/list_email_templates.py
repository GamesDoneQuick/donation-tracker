from django.core.management.base import BaseCommand, CommandError

import post_office.models

class Command(BaseCommand):
    help = 'List all e-mail templates'

    def add_arguments(self, parser):
        parser.add_argument('-f', '--filter', help='filter by name', default='')

    def handle(self, *args, **options):
        templateList = post_office.models.EmailTemplate.objects.all()
        
        if 'filter' in options:
            templateList = templateList.filter(name__icontains=options['filter'])

        if templateList.exists():
            for template in templateList:
                print('{0}'.format(template.name))
        else:
            print("No templates found.")
