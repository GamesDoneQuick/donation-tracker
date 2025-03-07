import { APIRun, PaginationInfo } from '@public/apiv2/APITypes';

import { getFixtureEvent } from '@spec/fixtures/event';
import { getFixtureTalent } from '@spec/fixtures/talent';

export function getFixtureRun(overrides?: Partial<APIRun>): APIRun {
  return {
    id: 1,
    type: 'speedrun',
    order: 1,
    event: getFixtureEvent(overrides?.event),
    starttime: '2024-01-01T12:00:00-05:00',
    endtime: '2024-01-01T13:00:00-05:00',
    run_time: '0:50:00',
    setup_time: '0:10:00',
    anchor_time: null,
    name: 'Start Run',
    display_name: '',
    twitch_name: '',
    description: 'The first run of the event',
    category: 'any%',
    coop: false,
    onsite: 'ONSITE',
    console: 'NES',
    release_year: 1988,
    runners: [getFixtureTalent()],
    hosts: [],
    commentators: [],
    layout: 'standard',
    video_links: [],
    priority_tag: null,
    tags: [],
    ...overrides,
  };
}

export function getFixturePagedRuns(overrides?: Partial<APIRun>[]): PaginationInfo<APIRun> {
  overrides = [
    { ...overrides?.[0] },
    {
      id: 2,
      order: 2,
      starttime: '2024-01-01T13:00:00-05:00',
      endtime: '2024-01-01T13:30:00-05:00',
      run_time: '0:20:00',
      setup_time: '0:10:00',
      anchor_time: '2024-01-01T13:00:00-05:00',
      name: 'Anchored Run',
      description: 'The anchored run',
      ...overrides?.[1],
    },
    {
      id: 3,
      order: 3,
      starttime: '2024-01-01T13:30:00-05:00',
      endtime: '2024-01-01T14:30:00-05:00',
      run_time: '0:50:00',
      setup_time: '0:10:00',
      name: 'Finale Run',
      category: 'any%',
      ...overrides?.[2],
    },
    {
      id: 4,
      order: null,
      starttime: null,
      endtime: null,
      run_time: '0:50:00',
      setup_time: '0:10:00',
      name: 'Unordered Run',
      description: 'Possible bonus run',
      ...overrides?.[3],
    },
    {
      id: 5,
      order: null,
      starttime: null,
      endtime: null,
      run_time: '0:00:00',
      setup_time: '0:00:00',
      name: 'Unordered Draft Run',
      description: 'No duration set',
      ...overrides?.[4],
    },
    ...(overrides != null ? overrides.slice(5) : []),
  ];
  return {
    count: overrides.length,
    previous: null,
    next: null,
    results: overrides.map(o => getFixtureRun(o)),
  };
}
