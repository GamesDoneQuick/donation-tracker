import { Incentive } from '../../bundles/tracker/event_details/EventDetailsTypes';

export function getFixtureBid(overrides?: Partial<Incentive>): Incentive {
  return {
    id: 1,
    name: 'Test Incentive',
    amount: 0,
    runname: 'Test Run',
    order: 1,
    chain: false,
    ...overrides,
  };
}
