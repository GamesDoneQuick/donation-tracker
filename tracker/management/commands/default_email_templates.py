import post_office.models

from tracker import prizemail, auth, commandutil

_default_templates = {
    auth.default_password_reset_template_name(): auth.default_password_reset_template(),
    auth.default_registration_template_name(): auth.default_registration_template(),
    auth.default_volunteer_registration_template_name(): auth.default_volunteer_registration_template(),
    prizemail.default_prize_winner_template_name(): prizemail.default_prize_winner_template(),
    prizemail.default_prize_contributor_template_name(): prizemail.default_prize_contributor_template(),
    prizemail.default_prize_winner_accept_template_name(): prizemail.default_prize_winner_accept_template(),
    prizemail.default_prize_shipping_template_name(): prizemail.default_prize_shipping_template(),
    prizemail.default_activate_prize_handlers_template_name(): prizemail.default_activate_prize_handlers_template(),
}


def email_template_name(arg):
    parts = arg.partition(':')
    template_obj = _default_templates[parts[0]]
    custom_name = None
    if parts[1] == ':':
        if parts[2]:
            custom_name = parts[2]
        else:
            raise Exception('Must specify custom name after colon')
    return (template_obj, custom_name)


class Command(commandutil.TrackerCommand):
    help = 'Generates all default mail templates that are not currently in the database'

    def add_arguments(self, parser):
        command_group = parser.add_mutually_exclusive_group(required=True)
        command_group.add_argument(
            '-l', '--list', help='List all default email templates', action='store_true'
        )
        command_group.add_argument(
            '-c',
            '--create',
            help='Create the specified template(s) (use the format <default>:<name> to specify a custom name in the database)',
            nargs='+',
            type=email_template_name,
        )
        command_group.add_argument(
            '-a',
            '--create-all',
            help='Create all known templates(s)',
            action='store_true',
        )
        parser.add_argument(
            '-o',
            '--overwrite',
            help='Overwrite existing templates even if they exist already',
            action='store_true',
            default=False,
        )
        parser.add_argument(
            '-p',
            '--prefix',
            help='Add a prefix to all names (only applies when a custom name is not specified)',
            action='store_true',
            default='',
        )

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        if options['list']:
            for option in _default_templates:
                self.message(option, 0)
            return

        if options['create']:
            templates = options['create']

        if options['create_all']:
            templates = map(email_template_name, _default_templates)

        templates = [(x[0], x[1] or (options['prefix'] + x[0].name)) for x in templates]

        for create in templates:
            found = post_office.models.EmailTemplate.objects.filter(name=create[1])
            if found.exists():
                if options['overwrite']:
                    target_template = found[0]
                    self.message(
                        f'Overwriting email template {create[1]} (id={target_template.id})',
                        1,
                    )
                    for field in target_template._meta.fields:
                        if field.name not in ['id', 'created', 'last_updated']:
                            setattr(
                                target_template,
                                field.name,
                                getattr(create[0], field.name),
                            )
                    target_template.name = create[1]
                    target_template.save()
                else:
                    self.message(
                        f'Skipping email template {create[1]} because it already exists',
                        1,
                    )
            else:
                self.message(f'Creating email template {create[1]}', 1)
                create[0].name = create[1]
                create[0].save()

        self.message('Done.', 1)
