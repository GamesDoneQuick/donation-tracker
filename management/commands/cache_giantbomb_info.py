import time
import json
import urllib
import datetime
import dateutil.parser
import re
import math

from django.core.management.base import CommandError

from django.conf import settings

import tracker.models as models
import tracker.viewutil as viewutil
import tracker.util as util
import tracker.commandutil as commandutil

_SETTINGS_KEY = 'GIANTBOMB_API_KEY'


class Command(commandutil.TrackerCommand):
    help = "(re-)cache a run's information w.r.t. the GiantBomb games database"

    def __init__(self):
        super(Command, self).__init__()
        self.compiled_cleaning_expression = re.compile('race|all bosses|\\w+%|\\w+ %')
        self.found_ambiguous_searched = False

    def add_arguments(self, parser):
        parser.add_argument(
            '-k',
            '--api-key',
            help='specify the api key to use (You can also set "{0}" in settings.py)'.format(
                _SETTINGS_KEY
            ),
            required=False,
            default=None,
        )
        parser.add_argument(
            '-t',
            '--throttle-rate',
            help='Number of seconds to put between requests. The default (non-paid) giantbomb api throttle is supposedly 200 requests per resrouce per hour.',
            default=(60.0 * 60.0) / 200.0,
            required=False,
        )
        selection_group = parser.add_mutually_exclusive_group(required=True)
        selection_group.add_argument(
            '-e', '--event', help='specify an event to synchronize'
        )
        selection_group.add_argument(
            '-r', '--run', help='Specify a specific run to synchronize', type=int
        )
        selection_group.add_argument(
            '-a',
            '--all',
            help='Synchronizes _all_ runs in the database (warning, due to giantbomb api throttling, this may take a long, long time.',
            action='store_true',
            default=False,
        )
        parser.add_argument(
            '-f',
            '--filter',
            help='A regex for game names to include (uses standard python regex syntax',
            required=False,
            default=None,
        )
        parser.add_argument(
            '-x',
            '--exclude',
            help='A regex for game names to exclude (a common one might be ".*setup.*"). Always case-insensitive',
            required=False,
            default=None,
        )
        id_group = parser.add_mutually_exclusive_group(required=False)
        id_group.add_argument(
            '-s',
            '--skip-with-id',
            help='Skip any games which already have a giantbomb id',
            action='store_true',
            default=False,
            required=False,
        )
        id_group.add_argument(
            '-g',
            '--ignore-id',
            help='Ignore the id on runs (helpful if an id was set incorrectly',
            action='store_true',
            default=False,
            required=False,
        )
        parser.add_argument(
            '-i',
            '--interactive',
            help='Run in interactive mode. Should be used with -s to avoid redundant queries',
            action='store_true',
            default=False,
            required=False,
        )
        parser.add_argument(
            '-l',
            '--limit',
            help='Specify the maximum number of runs to return in a search query',
            default=100,
            type=int,
            required=False,
        )

    def clean_game_name(self, name):
        return self.compiled_cleaning_expression.sub('', name)

    def build_search_url(self, name):
        # I am assuming a match will be found within the first 50 entries, if not, just edit it yourself (I'm too lazy to do a proper paging search right now)
        search_url_base = 'http://www.giantbomb.com/api/search/?api_key={key}&format=json&query={game}&resources=game&field_list=name,id,original_release_date,platforms&limit={limit}'
        return search_url_base.format(
            **dict(
                key=self.api_key, game=urllib.parse.quote(name), limit=self.query_limit
            )
        )

    def build_query_url(self, id):
        query_url_base = 'http://www.giantbomb.com/api/game/3030-{game_id}/?api_key={key}&format=json&field_list=id,name,original_release_date,platforms'
        return query_url_base.format(**dict(key=self.api_key, game_id=id))

    def parse_query_results(self, search_result):
        parsed_release_date = None
        if search_result['original_release_date'] is not None:
            parsed_release_date = dateutil.parser.parse(
                search_result['original_release_date']
            ).year
        return dict(
            name=str(search_result['name']),
            giantbomb_id=search_result['id'],
            release_year=parsed_release_date,
            platforms=list(
                [x['abbreviation'] for x in search_result['platforms'] or []]
            ),
        )

    def process_query(self, run, search_result):
        parsed = self.parse_query_results(search_result)

        if run.name != parsed['name']:
            self.message(
                'Setting run {0} name to {1}'.format(run.name, parsed['name']), 2
            )
            if self.compiled_cleaning_expression.search(run.name):
                self.message(
                    'Detected run name {0} (id={1}) may have category information embedded in it.'.format(
                        run.name, run.id
                    ),
                    0 if self.interactive else 1,
                )
                if self.interactive:
                    self.message(
                        'Please set a category for this run (hit enter to leave as {0})'.format(
                            run.category
                        ),
                        0,
                    )
                    category = input(' -> ')
                    if category != '':
                        run.category = category
            run.name = parsed['name']

        if run.giantbomb_id != parsed['giantbomb_id']:
            self.message(
                'Setting run {0} giantbomb_id to {1}'.format(
                    run.name, parsed['giantbomb_id']
                ),
                2,
            )
            run.giantbomb_id = parsed['giantbomb_id']

        if parsed['release_year'] is None:
            if self.interactive:
                self.message('No release date found for {0}'.format(run.name), 0)
                val = None
                while not isinstance(val, int):
                    self.message(
                        'Enter the release year (leave blank to leave as is): ', 0
                    )
                    year = input(' -> ')
                    if year == '':
                        break
                    val = util.try_parse_int(year)
                if val is not None:
                    run.release_year = val
            else:
                self.message(
                    'No release date info found for {0} (id={1}), you will need to fix this manually.'.format(
                        run.name, run.id
                    )
                )
        elif run.release_year != parsed['release_year']:
            self.message(
                'Setting run {0} release_year to {1}'.format(
                    run.name, parsed['release_year']
                ),
                2,
            )
            run.release_year = parsed['release_year']

        platform_count = len(parsed['platforms'])
        if run.console in parsed['platforms']:
            self.message(
                'Console already set for {0} to {1}.'.format(run.name, run.console), 0
            )
        elif platform_count != 1:
            if platform_count == 0:
                self.message('No platforms found for {0}'.format(run.name), 0)
            else:
                self.message('Multiple platforms found for {0}'.format(run.name), 0)
            self.message('Currently : {0}'.format(run.console or '<unset>'), 0)
            if self.interactive:
                val = None
                if platform_count == 0:
                    self.message(
                        'Select a console, or enter a name manually (leave blank to keep as is):'
                    )
                else:
                    self.message('Enter a console name (leave blank to keep as is):')
                    i = 1
                    for platform in parsed['platforms']:
                        self.message('{0}) {1}'.format(i, platform), 0)
                        i += 1
                    console = input(' -> ')
                    if console != '':
                        val = util.try_parse_int(console)
                        if val is not None and val >= 1 and val <= platform_count:
                            run.console = parsed['platforms'][val - 1]
                        else:
                            run.console = console
            elif not run.console:
                self.message(
                    'Multiple platforms found for {0}, leaving as is for now.'.format(
                        run.name
                    ),
                    0,
                )
        else:
            platform = parsed['platforms'][0]
            if run.console != platform:
                self.message(
                    'Setting console for {0} to {1}'.format(run.name, platform), 0
                )
                run.console = platform

        run.save()

    def filter_none_dates(self, entries):
        return list(
            [
                entry
                for entry in entries
                if self.parse_query_results(entry)['release_year'] is not None
            ]
        )

    def process_search(self, run, cleaned_run_name, search_results):
        exact_matches = []
        potential_matches = []
        for response in search_results:
            if response['name'].lower() == cleaned_run_name.lower():
                self.message('Found exact match {0}'.format(response['name']), 2)
                exact_matches.append(response)
            else:
                potential_matches.append(response)

        # If we find any exact matches, prefer those over any potential matches
        if len(exact_matches) > 0:
            potential_matches = exact_matches

        # If we find any matches with release dates, prefer those over any matches without release dates
        filter_no_date = self.filter_none_dates(potential_matches)
        if len(filter_no_date) > 0:
            potential_matches = filter_no_date

        if len(potential_matches) == 0:
            self.message('No matches found for {0}'.format(cleaned_run_name))
        elif len(potential_matches) > 1:
            if self.interactive:
                self.message(
                    'Multiple matches found for {0}, please select one:'.format(
                        cleaned_run_name
                    ),
                    0,
                )
                self.message('Possibilities:', 3)
                self.message('{0}'.format(potential_matches), 3)
                num_matches = len(potential_matches)
                for i in range(0, num_matches):
                    parsed = self.parse_query_results(potential_matches[i])
                    self.message(
                        '{0}) {1} ({2}) for {3}'.format(
                            i + 1,
                            parsed['name'],
                            parsed['release_year'],
                            ', '.join(parsed['platforms'] or ['(Unknown)']),
                        ),
                        0,
                    )
                val = None
                while not isinstance(val, int) or (val < 1 or val > num_matches):
                    self.message(
                        'Please select a value between 1 and {0} (enter a blank line to skip)'.format(
                            num_matches
                        ),
                        0,
                    )
                    match = input(' -> ')
                    if match == '':
                        val = None
                        break
                    val = util.try_parse_int(match)
                if val is not None and val >= 1 and val <= num_matches:
                    self.process_query(run, potential_matches[val - 1])
                else:
                    self.found_ambiguous_searched = True
            else:
                self.message(
                    'Multiple matches found for {0}, skipping for now'.format(
                        cleaned_run_name
                    )
                )
                self.found_ambiguous_searched = True
        else:
            self.process_query(run, potential_matches[0])

    def response_good(self, data):
        if data['error'] == 'OK':
            return True
        else:
            self.message('Error: {0}'.format(data['error']))
            return False

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        self.message(str(options), 3)

        self.api_key = options['api_key']
        if options['api_key'] is None:
            self.api_key = getattr(settings, _SETTINGS_KEY, None)

        if not self.api_key:
            raise CommandError(
                'No API key was supplied, and {0} was not set in settings.py, cannot continue.'.format(
                    _SETTINGS_KEY
                )
            )

        filter_regex = None
        if options['filter']:
            filter_regex = re.compile(options['filter'], re.IGNORECASE)

        exclude_regex = None
        if options['exclude']:
            exclude_regex = re.compile(options['exclude'], re.IGNORECASE)

        run_list = models.SpeedRun.objects.all()

        if options['event'] is not None:
            try:
                event = viewutil.get_event(options['event'])
            except models.Event.DoesNotExist:
                CommandError('Error, event {0} does not exist'.format(options['event']))
            run_list = run_list.filter(event=event)
        elif options['run'] is not None:
            run_list = run_list.filter(id=int(options['run']))

        self.query_limit = options['limit']
        throttle_float = float(options['throttle_rate'])
        throttle_seconds = int(options['throttle_rate'])
        throttle_micros = int((throttle_float - math.floor(throttle_float)) * (10 ** 9))
        throttle_rate = datetime.timedelta(
            seconds=throttle_seconds, microseconds=throttle_micros
        )
        self.ignore_id = options['ignore_id']
        self.interactive = options['interactive']
        self.skip_with_id = options['skip_with_id']

        last_api_call_time = datetime.datetime.min

        for run in run_list:
            if (not filter_regex or filter_regex.match(run.name)) and (
                not exclude_regex or not exclude_regex.match(run.name)
            ):
                next_api_call_time = last_api_call_time + throttle_rate
                if next_api_call_time > datetime.datetime.now():
                    wait_delta = next_api_call_time - datetime.datetime.now()
                    wait_time = max(
                        0.0,
                        (wait_delta.seconds + wait_delta.microseconds / (10.0 ** 9)),
                    )
                    self.message(
                        'Wait {0} seconds for next url call'.format(wait_time), 2
                    )
                    time.sleep(wait_time)
                if run.giantbomb_id and not self.ignore_id:
                    if not self.skip_with_id:
                        self.message(
                            'Querying id {0} for {1}'.format(run.giantbomb_id, run)
                        )
                        query_url = self.build_query_url(run.giantbomb_id)
                        self.message('(url={0})'.format(query_url), 2)
                        data = json.loads(urllib.request.urlopen(query_url).read())
                        last_api_call_time = datetime.datetime.now()

                        if self.response_good(data):
                            self.process_query(run, data['results'])
                    else:
                        self.message(
                            'Skipping run {0} with giantbomb id {1}'.format(
                                run.name, run.giantbomb_id
                            )
                        )
                else:
                    cleaned_name = self.clean_game_name(run.name)
                    search_url = self.build_search_url(cleaned_name)
                    if cleaned_name != run.name:
                        self.message(
                            'Cleaned {0} => {1}'.format(run.name, cleaned_name), 2
                        )
                    if self.ignore_id:
                        self.message(
                            'Overriding giantbomb_id {0} for {1}'.format(
                                run.giantbomb_id, cleaned_name
                            )
                        )
                    self.message('Searching for {0}'.format(cleaned_name))
                    self.message('(url={0})'.format(search_url), 2)
                    data = json.loads(urllib.request.urlopen(search_url).read())
                    last_api_call_time = datetime.datetime.now()

                    if self.response_good(data):
                        self.process_search(run, cleaned_name, data['results'])
            else:
                self.message('Run {0} does not match filters.'.format(run.name), 2)

        if self.found_ambiguous_searched:
            self.message(
                '\nOne or more objects could not be synced due to ambiguous run names. Re-run the command with options -is to resolve these interactively'
            )
            self.message(
                '(be sure to also set --throttle-rate=0 to preserve your sanity!)'
            )

        self.message('\nDone.')
