import { Talent } from '@public/apiv2/Models';

export function getFixtureTalent(overrides?: Partial<Talent>): Talent {
  return {
    id: 1,
    type: 'talent',
    name: 'Famous',
    stream: 'https://twitch.tv/famous',
    twitter: 'Famous',
    youtube: 'Famous',
    platform: 'TWITCH',
    pronouns: 'any/all',
    ...overrides,
  };
}
