import { Event, PaginationInfo } from '@public/apiv2/APITypes';

export function getFixtureEvent(overrides?: Partial<Event>): Event {
  return {
    id: 1,
    type: 'event',
    short: 'test',
    name: 'Test Event',
    hashtag: '',
    datetime: '2024-01-01T11:30:00-05:00',
    timezone: 'America/New_York',
    receivername: 'Receiver',
    receiver_short: 'R',
    receiver_solicitation_text: 'Click here to receive emails from Receiver',
    receiver_logo: 'https://example.com/logo.png',
    receiver_privacy_policy: 'https://example.com/privacy/',
    paypalcurrency: 'USD',
    use_one_step_screening: true,
    allow_donations: true,
    locked: false,
    ...overrides,
  };
}

export function getFixturePagedEvent(overrides?: Partial<Event>): PaginationInfo<Event> {
  return {
    count: 1,
    previous: null,
    next: null,
    results: [getFixtureEvent(overrides)],
  };
}
