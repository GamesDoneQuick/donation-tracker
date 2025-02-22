import { combinedReducer, StoreState } from '@tracker/Store';

import { getFixtureEvent } from '@spec/fixtures/event';

import { getEvent } from './EventStore';

describe('EventStore', () => {
  const event = getFixtureEvent();
  let state: StoreState;

  beforeEach(() => {
    state = {
      // @ts-expect-error `type: INIT` is an internal thing that isn't part of our reducers.
      ...combinedReducer(undefined, { type: 'INIT' }),
      events: { loading: false, events: { '1': event } },
    };
  });

  describe('#getEvent', () => {
    describe('numeric id', () => {
      it('works for events that exist', () => {
        expect(getEvent(state, { eventId: '1' })).toBe(event);
      });

      it('returns nothing for events that do not exist', () => {
        expect(getEvent(state, { eventId: '2' })).toBeFalsy();
      });
    });

    describe('short name', () => {
      it('works for events that exist', () => {
        expect(getEvent(state, { eventId: 'test' })).toBe(event);
      });

      it('returns nothing for events that do not exist', () => {
        expect(getEvent(state, { eventId: 'nonsense' })).toBeFalsy();
      });
    });
  });
});
