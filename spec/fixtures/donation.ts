import { APIDonation, PaginationInfo } from '@public/apiv2/APITypes';

export function getFixtureDonation(overrides?: Partial<APIDonation>): APIDonation {
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

export function getFixturePagedDonations(overrides?: Partial<APIDonation>[]): PaginationInfo<APIDonation> {
  overrides = [{ ...overrides?.[0] }, ...(overrides ?? []).slice(1)];
  return {
    count: overrides.length,
    previous: null,
    next: null,
    results: overrides.map(o => getFixtureDonation(o)),
  };
}
