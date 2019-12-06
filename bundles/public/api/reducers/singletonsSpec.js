import singletons from './singletons';

describe('singletons reducers', () => {
  describe('#loadMe', () => {
    const state = { other_thing: {} };
    const me = { username: 'jazzaboo' };
    let result;
    beforeEach(() => {
      result = singletons(state, { type: 'LOAD_ME', me });
    });

    it('adds "me" to the state', () => {
      expect(result.me).toBe(me);
    });

    it('does not mutate other state', () => {
      expect(result.other_thing).toBe(state.other_thing);
    });

    it('returns a new state', () => {
      expect(result).not.toBe(state);
    });
  });
});
