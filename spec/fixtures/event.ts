import { Event } from '../../bundles/tracker/events/EventTypes';

export function getFixtureEvent(overrides?: Partial<Event>): Event {
  return {
    id: '1',
    short: 'test',
    name: 'Test Event',
    canonicalUrl: '/testserver/tracker/events/1',
    public: 'Test Event',
    useOneStepScreening: false,
    timezone: 'America/New_York',
    locked: false,
    paypalEmail: 'paypal@example.com',
    paypalCurrency: 'USB',
    paypalImgurl: '',
    targetAmount: 5000,
    allowDonations: true,
    minimumDonation: 5,
    allowedPrizeCountries: [],
    disallowedPrizeRegions: [],
    prizeAcceptDeadlineDelta: 30,
    amount: 0,
    count: 0,
    max: 0,
    avg: 0,
    ...overrides,
  };
}
