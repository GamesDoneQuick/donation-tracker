import post_office.models
import tracker.commandutil as commandutil


class Command(commandutil.TrackerCommand):
    help = 'List all e-mail templates'

    def add_arguments(self, parser):
        parser.add_argument('-f', '--filter', help='filter by name', default='')

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        template_list = post_office.models.EmailTemplate.objects.all()

        if 'filter' in options:
            template_list = template_list.filter(name__icontains=options['filter'])

        if template_list.exists():
            for template in template_list:
                self.message('{0}'.format(template.name), 0)
        else:
            self.message('No templates found.')
