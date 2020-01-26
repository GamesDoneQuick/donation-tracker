import { Prize } from '../../bundles/tracker/prizes/PrizeTypes';

export function getFixturePrize(overrides?: Partial<Prize>): Prize {
  return {
    id: '123',
    name: 'Fixture Prize',
    public: 'Fixture Prize',
    description: 'Fixture Prize Description',
    shortDescription: 'Fixture Prize Short Description',
    canonicalUrl: 'http://localhost:8000/tracker/prizes/123',
    minimumBid: 5,
    sumDonations: false,
    eventId: '1',
    randomDraw: true,
    keyCode: false,
    requiresShipping: false,
    customCountryFilter: false,
    allowedPrizeCountries: [],
    disallowedPrizeRegions: [],
    numWinners: 0,
    maxWinners: 1,
    maxMultiWin: 1,
    ...overrides,
  };
}
