"""
This is the set of lookups that need to be included in settings.py in order to 
make the `ajax_selects` app work correctly. I'm tired of updating this crap 
everywhere all the time, so just import this dictionary.
"""

AJAX_LOOKUP_CHANNELS = {
  'donation'     : ('tracker.lookups', 'DonationLookup'),
  'donor'        : ('tracker.lookups', 'DonorLookup'),
  'run'          : ('tracker.lookups', 'RunLookup'),
  'event'        : ('tracker.lookups', 'EventLookup'),
  'bidtarget'    : ('tracker.lookups', 'BidTargetLookup'),
  'bid'          : ('tracker.lookups', 'BidLookup'),
  'allbids'      : ('tracker.lookups', 'AllBidLookup'),
  'prize'        : ('tracker.lookups', 'PrizeLookup'),
  'runner'       : ('tracker.lookups', 'RunnerLookup'),
  'country'      : ('tracker.lookups', 'CountryLookup'),
  'countryregion': ('tracker.lookups', 'CountryRegionLookup'),
  'user'         : ('tracker.lookups', 'UserLookup'),
}
