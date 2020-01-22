import { getTopLevelIncentives } from './EventDetailsStore';
import { combinedReducer, StoreState } from '../Store';
import { getFixtureBid } from '../../../spec/fixtures/bid';

describe('EventDetailsStore', () => {
  const bid1 = getFixtureBid({ id: 1, order: 50 });
  const bid2 = getFixtureBid({ id: 2, order: 3 });
  let state: StoreState;

  beforeEach(() => {
    state = combinedReducer(undefined, { type: 'INIT' });
    state = {
      ...state,
      eventDetails: { ...state.eventDetails, availableIncentives: { '1': bid1, '2': bid2 } },
    };
  });

  describe('#getTopLevelIncentives', () => {
    it('returns top-level incentives in order', () => {
      expect(getTopLevelIncentives(state)).toEqual([bid2, bid1]);
    });
  });
});
