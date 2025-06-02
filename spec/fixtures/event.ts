import { APIEvent, PaginationInfo } from '@public/apiv2/APITypes';
import { sum } from '@public/util/reduce';

type ComputedFields =
  | 'use_one_step_screening'
  | 'locked'
  | 'amount'
  | 'donation_count'
  | 'donation_total'
  | 'donation_avg'
  | 'donation_max'
  | 'donation_med';

function median(values: number[], fallback = 0) {
  if (values.length === 0) {
    return fallback;
  } else if (values.length % 2 === 0) {
    return (values[values.length / 2 - 1] + values[values.length]) / 2;
  } else {
    return values[Math.floor(values.length / 2)];
  }
}

export function getFixtureEvent(overrides?: Omit<Partial<APIEvent>, ComputedFields>, amounts?: number[]): APIEvent {
  const computed: Pick<APIEvent, ComputedFields> = {
    locked: overrides?.archived ?? false,
    use_one_step_screening: overrides?.screening_mode !== 'two_pass',
  };
  if (amounts) {
    computed.donation_count = amounts.length;
    computed.donation_total = amounts.reduce(sum, 0);
    computed.amount = computed.donation_total;
    computed.donation_avg = amounts.length ? computed.donation_total / amounts.length : 0;
    computed.donation_max = Math.max(0, ...amounts);
    computed.donation_med = median(amounts);
  }
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
    screening_mode: 'one_pass',
    allow_donations: true,
    archived: false,
    draft: false,
    minimumdonation: 5,
    maximum_paypal_donation: null,
    ...computed,
    ...overrides,
  };
}

export function getFixturePagedEvent(
  overrides?: Omit<Partial<APIEvent>, ComputedFields>,
  amounts?: number[],
): PaginationInfo<APIEvent> {
  return {
    count: 1,
    previous: null,
    next: null,
    results: [getFixtureEvent(overrides, amounts)],
  };
}
