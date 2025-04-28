import { APIInterview, PaginationInfo } from '@public/apiv2/APITypes';

import { getFixtureEvent } from './event';
import { getFixtureTalent } from './talent';

export function getFixtureInterview(overrides?: Partial<APIInterview>): APIInterview {
  return {
    type: 'interview',
    id: 101,
    event: getFixtureEvent(typeof overrides?.event === 'number' ? { id: overrides.event } : overrides?.event),
    interviewers: [getFixtureTalent({ name: 'feasel' })],
    subjects: [getFixtureTalent({ name: 'PJ' })],
    topic: 'Why are you a Chaos Elemental?',
    social_media: false,
    public: true,
    prerecorded: false,
    producer: 'Skavenger216',
    camera_operator: 'klinkit',
    anchor: null,
    order: 1,
    suborder: 1,
    tags: [],
    length: '00:15:00',
    ...overrides,
  };
}

export function getFixturePagedInterviews(overrides?: Array<Partial<APIInterview>>): PaginationInfo<APIInterview> {
  overrides = [{ ...overrides?.[0] }, ...(overrides != null ? overrides.slice(1) : [])];
  return {
    count: overrides.length,
    previous: null,
    next: null,
    results: overrides.map(o => getFixtureInterview(o)),
  };
}
