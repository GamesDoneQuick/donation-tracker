import { APIAd, PaginationInfo } from '@public/apiv2/APITypes';

import { getFixtureEvent } from './event';

export function getFixtureAd(overrides?: Partial<APIAd>): APIAd {
  return {
    type: 'ad',
    id: 201,
    event: getFixtureEvent(typeof overrides?.event === 'number' ? { id: overrides.event } : overrides?.event),
    anchor: null,
    order: 1,
    suborder: 101, // just to not collide with interviews
    sponsor_name: 'Contoso',
    ad_name: 'Contoso University',
    ad_type: 'IMAGE',
    filename: 'foobar.jpg',
    blurb: 'Learn to Code',
    tags: [],
    length: '00:00:30',
    ...overrides,
  };
}

export function getFixturePagedAds(overrides?: Partial<APIAd>[]): PaginationInfo<APIAd> {
  overrides = [{ ...overrides?.[0] }, ...(overrides != null ? overrides.slice(1) : [])];
  return {
    count: overrides.length,
    previous: null,
    next: null,
    results: overrides.map(o => getFixtureAd(o)),
  };
}
