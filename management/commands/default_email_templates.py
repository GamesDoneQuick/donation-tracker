from django.core.management.base import BaseCommand, CommandError

import post_office

import tracker.prizemail as prizemail
import tracker.auth as auth
import tracker.commandutil as commandutil

_defaultTemplates = {
    auth.default_password_reset_template_name(): auth.default_password_reset_template(),
    auth.default_registration_template_name(): auth.default_registration_template(),
    prizemail.default_prize_winner_template_name(): prizemail.default_prize_winner_template(),
    prizemail.default_prize_contributor_template_name(): prizemail.default_prize_contributor_template(),
    prizemail.default_prize_winner_accept_template_name(): prizemail.default_prize_winner_accept_template(),
    prizemail.default_prize_shipping_template_name(): prizemail.default_prize_shipping_template(),
    prizemail.default_activate_prize_handlers_template_name(): prizemail.default_activate_prize_handlers_template(),
}

def email_template_name(arg):
    parts = arg.partition(':')
    templateObj = _defaultTemplates[parts[0]]
    customName = None
    if parts[1] == ':':
        if parts[2]:
            customName = parts[2]
        else:
            raise Exception("Must specify custom name after colon")
    return (templateObj,customName)
         

class Command(commandutil.TrackerCommand):
    help = "Generates all default mail templates that are not currently in the database"

    def add_arguments(self, parser):
        commandGroup = parser.add_mutually_exclusive_group(required=True)
        commandGroup.add_argument('-l', '--list', help='List all default email templates', action='store_true')
        commandGroup.add_argument('-c', '--create', help='Create the specified template(s) (use the format <default>:<name> to specify a custom name in the database)', nargs='+', type=email_template_name)
        commandGroup.add_argument('-a', '--create-all', help='Create all known templates(s)', action='store_true')
        parser.add_argument('-f', '--force', help='Force run the command even if it would overwrite existing data (by default, the command will abort if any existing objects would be overwritten)', action='store_true', default=False)
        parser.add_argument('-p', '--prefix', help='Add a prefix to all names (only applies when a custom name is not specified)', action='store_true', default='')

    def check_validity(self, createList, force=False):
        currentNames = set()
        for create in createList:
            if create[1] in currentNames:
                raise Exception("Name {0} was specified twice".format(create[1]))
            if not force and post_office.models.EmailTemplate.objects.filter(name=create[1]).exists():
                raise Exception("Name {0} already exsits in database".format(create[1]))  
            currentNames.add(create[1])

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        self.prefix = options['prefix']

        if options['list']:
            for option in _defaultTemplates.keys():
                self.message(option, 0)
            return
 
        if options['create']:
            self.templates = options['create']

        if options['create_all']:
            self.templates = list(map(email_template_name, _defaultTemplates.keys()))

        self.templates = list(map(lambda x: (x[0], x[1] or (options['prefix'] + x[0].name)), self.templates))

        self.check_validity(self.templates, options['force'])

        for create in self.templates:
            found = post_office.models.EmailTemplate.objects.filter(name=create[1])
            if found.exists():
                targetTemplate = found[0]
                self.message("Overwriting email template {0} (id={1})".format(create[1], targetTemplate.id), 1)
                for field in targetTemplate._meta.fields:
                    if field.name not in ['id', 'created', 'last_updated']:
                        setattr(targetTemplate, field.name, getattr(create[0], field.name))
                targetTemplate.name = create[1]
                targetTemplate.save()
            else:
                self.message("Creating email template {0}".format(create[1]), 1)
                create[0].name = create[1]
                create[0].save() 

        self.message("Done.", 1)

