import { APIPrize, PaginationInfo } from '@public/apiv2/APITypes';

import { getFixtureEvent } from '@spec/fixtures/event';

export function getFixturePrize(overrides?: Partial<APIPrize>): APIPrize {
  return {
    id: 123,
    type: 'prize',
    name: 'Fixture Prize',
    description: 'Fixture Prize Description',
    shortdescription: 'Fixture Prize Short Description',
    minimumbid: 5,
    sumdonations: false,
    event: getFixtureEvent(overrides?.event),
    state: 'ACCEPTED',
    startrun: null,
    endrun: null,
    starttime: null,
    endtime: null,
    start_draw_time: null,
    end_draw_time: null,
    image: 'https://example.com/image.png',
    altimage: 'https://example.com/altimage.png',
    imagefile: null,
    estimatedvalue: 5,
    provider: 'Workshop',
    creator: 'Workshop',
    creatorwebsite: 'https://example.com/',
    ...overrides,
  };
}

export function getFixturePagedPrizes(overrides: Array<Partial<APIPrize>> = [{}]): PaginationInfo<APIPrize> {
  return {
    count: overrides.length,
    previous: null,
    next: null,
    results: overrides.map(o => getFixturePrize(o)),
  };
}
