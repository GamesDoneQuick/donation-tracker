import { Donation } from '@gamesdonequick/donation-tracker-api-types';

export function getDonation(overrides?: Partial<Donation>): Donation {
  return {
    type: 'donation',
    id: 1,
    donor_name: '(Anonymous)',
    event: 1,
    domain: 'PAYPAL',
    transactionstate: 'COMPLETED',
    readstate: 'PENDING',
    commentstate: overrides?.comment ? 'PENDING' : 'ABSENT',
    amount: 5,
    currency: 'USD',
    timereceived: '2010-01-01T00:00:00Z',
    commentlanguage: 'un',
    pinned: false,
    bids: [],
    ...overrides,
  };
}
