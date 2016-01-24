import sys
import time
import json
import urllib
import urllib2
import datetime
import dateutil.parser
import readline
import re
import math

from django.core.management.base import BaseCommand, CommandError

import settings

import tracker.models as models
import tracker.viewutil as viewutil
import tracker.util as util
import tracker.commandutil as commandutil

_settingsKey = 'GIANTBOMB_API_KEY'


class Command(commandutil.TrackerCommand):
    help = "(re-)cache a run's information w.r.t. the GiantBomb games database"
    
    def __init__(self):
        super(Command, self).__init__()
        self.compiledCleaningExpression = re.compile('race|all bosses|\\w+%|\\w+ %')
        self.foundAmbigiousSearched = False
        
    def add_arguments(self, parser):
        parser.add_argument('-k', '--api-key', help='specify the api key to use (You can also set "{0}" in settings.py)'.format(_settingsKey), required=False, default=None)
        parser.add_argument('-t', '--throttle-rate', help='Number of seconds to put between requests. The default (non-paid) giantbomb api throttle is supposedly 200 requests per resrouce per hour.', default=(60.0*60.0)/200.0, required=False)
        selectionGroup = parser.add_mutually_exclusive_group(required=True)
        selectionGroup.add_argument('-e', '--event', help='specify an event to synchronize')
        selectionGroup.add_argument('-r', '--run', help='Specify a specific run to synchronize', type=int)
        selectionGroup.add_argument('-a', '--all', help='Synchronizes _all_ runs in the database (warning, due to giantbomb api throttling, this may take a long, long time.', action='store_true', default=False)
        parser.add_argument('-f', '--filter', help='A regex for game names to include (uses standard python regex syntax', required=False, default=None)
        parser.add_argument('-x', '--exclude', help='A regex for game names to exclude (a common one might be ".*setup.*"). Always case-insensitive', required=False, default=None)
        idGroup = parser.add_mutually_exclusive_group(required=False)
        idGroup.add_argument('-s', '--skip-with-id', help='Skip any games which already have a giantbomb id', action='store_true', default=False, required=False)
        idGroup.add_argument('-g', '--ignore-id', help='Ignore the id on runs (helpful if an id was set incorrectly', action='store_true', default=False, required=False)
        parser.add_argument('-i', '--interactive', help='Run in interactive mode. Should be used with -s to avoid redundant queries', action='store_true', default=False, required=False)
        parser.add_argument('-l', '--limit', help='Specify the maximum number of runs to return in a search query', default=100, type=int, required=False)
        
    def clean_game_name(self, name):
        return self.compiledCleaningExpression.sub('', name)

    def build_search_url(self, name):
        # I am assuming a match will be found within the first 50 entries, if not, just edit it yourself (I'm too lazy to do a proper paging search right now)
        searchUrlBase = "http://www.giantbomb.com/api/search/?api_key={key}&format=json&query={game}&resources=game&field_list=name,id,original_release_date,platforms&limit={limit}"
        return searchUrlBase.format(**dict(key=self.apiKey, game=urllib.quote(name), limit=self.queryLimit))

    def build_query_url(self, id):
        queryUrlBase = "http://www.giantbomb.com/api/game/3030-{game_id}/?api_key={key}&format=json&field_list=id,name,original_release_date,platforms"
        return queryUrlBase.format(**dict(key=self.apiKey, game_id=id))

    def parse_query_results(self, searchResult):
        parsedReleaseDate = None
        if searchResult['original_release_date'] != None:
            parsedReleaseDate = dateutil.parser.parse(searchResult['original_release_date']).year
        return dict(
            name=unicode(searchResult['name']),
            giantbomb_id=searchResult['id'],
            release_year=parsedReleaseDate,
            platforms=list(map(lambda x: x['abbreviation'], searchResult['platforms'] or []))
        )

    def process_query(self, run, searchResult):
        parsed = self.parse_query_results(searchResult)
        
        if run.name != parsed['name']:
            self.message(u"Setting run {0} name to {1}".format(run.name, parsed['name']), 2)
            if self.compiledCleaningExpression.search(run.name):
                self.message(u'Detected run name {0} (id={1}) may have category information embedded in it.'.format(run.name, run.id), 0 if self.interactive else 1)
                if self.interactive:
                    self.message(u'Please set a category for this run (hit enter to leave as {0})'.format(run.category), 0)
                    input = raw_input(' -> ')
                    if input != '':
                        run.category = input
            run.name = parsed['name']

        if run.giantbomb_id != parsed['giantbomb_id']:
            self.message(u"Setting run {0} giantbomb_id to {1}".format(run.name, parsed['giantbomb_id']), 2)
            run.giantbomb_id = parsed['giantbomb_id']
        
        if parsed['release_year'] == None:
            if self.interactive:
                self.message(u"No release date found for {0}".format(run.name), 0)
                val = None
                while not isinstance(val, int):
                    self.message(u"Enter the release year (leave blank to leave as is): ", 0)
                    input = raw_input(' -> ')
                    if input == '':
                        break
                    val = util.try_parse_int(input)
                if val != None:
                    run.release_year = val
            else:
                self.message(u"No release date info found for {0} (id={1}), you will need to fix this manually.".format(run.name, run.id))
        elif run.release_year != parsed['release_year']:
            self.message(u"Setting run {0} release_year to {1}".format(run.name, parsed['release_year']), 2)
            run.release_year = parsed['release_year']

        platformCount = len(parsed['platforms'])
        if run.console in parsed['platforms']:
            self.message(u"Console already set for {0} to {1}.".format(run.name, run.console), 0)
        elif platformCount != 1:
            if platformCount == 0:
                self.message(u"No platforms found for {0}".format(run.name), 0)
            else:
                self.message(u"Multiple platforms found for {0}".format(run.name), 0)
            self.message(u"Currently : {0}".format(run.console or "<unset>"), 0)
            if self.interactive:
                val = None
                if platformCount == 0:
                    self.message(u"Select a console, or enter a name manually (leave blank to keep as is):")
                else:
                    self.message(u"Enter a console name (leave blank to keep as is):")
                    i = 1
                    for platform in parsed['platforms']:
                        self.message("{0}) {1}".format(i, platform), 0)
                        i += 1
                    input = raw_input(' -> ')
                    if input != '':
                        val = util.try_parse_int(input)
                        if val != None and val >= 1 and val <= platformCount:
                            run.console = parsed['platforms'][val-1]
                        else:
                            run.console = input
            elif not run.console:
                    self.message(u"Multiple platforms found for {0}, leaving as is for now.".format(run.name), 0)
        else:
            platform = parsed['platforms'][0]
            if run.console != platform:
                self.message(u"Setting console for {0} to {1}".format(run.name, platform), 0)
                run.console = platform 
            
        run.save()
        
    def filter_none_dates(self, entries):
        return list(filter(lambda entry: self.parse_query_results(entry)['release_year'] != None, entries))

    def process_search(self, run, cleanedRunName, searchResults):
        exactMatches = []
        potentialMatches = []
        for response in searchResults:
            if response['name'].lower() == cleanedRunName.lower():
                self.message(u"Found exact match {0}".format(response['name']), 2)
                exactMatches.append(response)
            else:
                potentialMatches.append(response)

        # If we find any exact matches, prefer those over any potential matches
        if len(exactMatches) > 0:
            potentialMatches = exactMatches
        
        # If we find any matches with release dates, prefer those over any matches without release dates
        filterNoDate = self.filter_none_dates(potentialMatches)
        if len(filterNoDate) > 0:
            potentialMatches = filterNoDate
        
        if len(potentialMatches) == 0:
            self.message(u"No matches found for {0}".format(cleanedRunName))
        elif len(potentialMatches) > 1:
            if self.interactive:
                self.message(u"Multiple matches found for {0}, please select one:".format(cleanedRunName), 0)
                self.message(u"Possibilities:", 3)
                self.message(u"{0}".format(potentialMatches), 3)
                numMatches = len(potentialMatches)
                for i in range(0, numMatches):
                    parsed = self.parse_query_results(potentialMatches[i])
                    self.message(u"{0}) {1} ({2}) for {3}".format(i+1, parsed['name'], parsed['release_year'], ', '.join(parsed['platforms'] or ['(Unknown)'])), 0)
                val = None
                while not isinstance(val, int) or (val < 1 or val > numMatches):
                    self.message(u"Please select a value between 1 and {0} (enter a blank line to skip)".format(numMatches), 0)
                    input = raw_input(' -> ')
                    if input == '':
                        val = None
                        break
                    val = util.try_parse_int(input)
                if val != None and val >= 1 and val <= numMatches:
                    self.process_query(run, potentialMatches[val-1])
                else:
                    self.foundAmbigiousSearched = True
            else:
                self.message(u"Multiple matches found for {0}, skipping for now".format(cleanedRunName))
                self.foundAmbigiousSearched = True
        else:
            self.process_query(run, potentialMatches[0])

    def response_good(self, data):
        if data['error'] == 'OK':
            return True
        else:
            self.message("Error: {0}".format(data['error']))
            return False
    
    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        self.message(str(options),3)
    
        self.apiKey = options['api_key']
        if options['api_key'] == None:
            self.apiKey = getattr(settings, _settingsKey, None)
    
        if not self.apiKey:
            raise CommandError("No API key was supplied, and {0} was not set in settings.py, cannot continue.".format(_settingsKey))

        filterRegex = None
        if options['filter']:
            filterRegex = re.compile(options['filter'], re.IGNORECASE)
        
        excludeRegex = None
        if options['exclude']:
            excludeRegex = re.compile(options['exclude'], re.IGNORECASE)
        
        runlist = models.SpeedRun.objects.all()
        
        if options['event'] != None:
            try:
                event = viewutil.get_event(options['event'])
            except:
                CommandError("Error, event {0} does not exist".format(options['event']))
            runlist = runlist.filter(event=event)
        elif options['run'] != None:
            runlist = runlist.filter(id=int(options['run']))
        
        self.queryLimit = options['limit']
        throttleFloat = float(options['throttle_rate'])
        throttleSeconds = int(options['throttle_rate'])
        throttleMicroseconds = int((throttleFloat - math.floor(throttleFloat))*(10**9))
        throttleRate = datetime.timedelta(seconds=throttleSeconds, microseconds=throttleMicroseconds)
        self.ignoreId = options['ignore_id']
        self.interactive = options['interactive']
        self.skipWithId = options['skip_with_id']
        
        lastApiCallTime = datetime.datetime.min
        
        for run in runlist:
            if (not filterRegex or filterRegex.match(run.name)) and (not excludeRegex or not excludeRegex.match(run.name)):
                nextAPICallTime = lastApiCallTime + throttleRate
                if nextAPICallTime > datetime.datetime.now():
                    waitDelta = nextAPICallTime - datetime.datetime.now()
                    waitTime = max(0.0, (waitDelta.seconds + waitDelta.microseconds/(10.0**9)))
                    self.message("Wait {0} seconds for next url call".format(waitTime), 2)
                    time.sleep(waitTime)
                throttleNext = True
                if run.giantbomb_id and not self.ignoreId:
                    if not self.skipWithId:
                        self.message("Querying id {0} for {1}".format(run.giantbomb_id, run))
                        queryUrl = self.build_query_url(run.giantbomb_id)
                        self.message("(url={0})".format(queryUrl), 2)
                        data = json.loads(urllib2.urlopen(queryUrl).read())
                        lastApiCallTime = datetime.datetime.now()
                        
                        if self.response_good(data):
                            self.process_query(run, data['results'])
                    else:
                        self.message("Skipping run {0} with giantbomb id {1}".format(run.name, run.giantbomb_id))
                else:
                    cleanedName = self.clean_game_name(run.name)
                    searchUrl = self.build_search_url(cleanedName)
                    if cleanedName != run.name:
                        self.message("Cleaned {0} => {1}".format(run.name, cleanedName), 2)
                    if self.ignoreId:
                        self.message("Overriding giantbomb_id {0} for {1}".format(run.giantbomb_id, cleanedName))
                    self.message("Searching for {0}".format(cleanedName))
                    self.message("(url={0})".format(searchUrl), 2)
                    data = json.loads(urllib2.urlopen(searchUrl).read())
                    lastApiCallTime = datetime.datetime.now()
                    
                    if self.response_good(data):
                        self.process_search(run, cleanedName, data['results'])
            else:
                self.message('Run {0} does not match filters.'.format(run.name), 2)
        
        if self.foundAmbigiousSearched:
            self.message("\nOne or more objects could not be synced due to ambiguous run names. Re-run the command with options -is to resolve these interactively")
            self.message("(be sure to also set --throttle-rate=0 to preserve your sanity!)")
        
        self.message("\nDone.")

