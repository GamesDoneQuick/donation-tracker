import fetchMock from 'fetch-mock';
import thunk from 'redux-thunk';
import configureMockStore from 'redux-mock-store';

import singletons from './singletons';

const mockStore = configureMockStore([thunk.withExtraArgument({ apiRoot: 'http://testserver/' })]);

const expectActions = (store, creator, expected = []) => {
  store.dispatch(creator).then(() => {
    expect(store.getActions()).toEqual(expected);
  });
};

describe('singletons actions', () => {
  let action;
  let store;

  beforeEach(() => {
    fetchMock.restore();
  });

  describe('#fetchMe', () => {
    beforeEach(() => {
      action = singletons.fetchMe();
      store = mockStore();
    });

    it('returns a thunk', () => {
      expect(action).toEqual(jasmine.any(Function));
    });

    describe('when the thunk is called', () => {
      beforeEach(() => {
        fetchMock.restore().getOnce('path:/me', {
          body: { todos: ['do something'] },
          headers: { 'content-type': 'application/json' },
        });
      });

      it('dispatches a loading action for "me"', () => {
        store.dispatch(action).then(() => {
          expect(store.getActions()).toContain(
            jasmine.objectContaining({ type: 'MODEL_STATUS_LOADING', model: { type: 'me' } }),
          );
        });
      });

      it('sends a request to the ME endpoint', () => {
        store.dispatch(action).then(() => {
          expect(fetchMock.done());
        });
      });

      describe('when the call succeeds', () => {
        const ME_DATA = { username: 'jazzaboo' };
        beforeEach(() => {
          fetchMock.restore().getOnce('path:/me', {
            body: ME_DATA,
            headers: { 'content-type': 'application/json' },
          });
        });

        it('dispatches a model success for "me"', () => {
          store.dispatch(action).then(() => {
            expect(store.getActions()).toContain(
              jasmine.objectContaining({ type: 'MODEL_STATUS_SUCCESS', model: { type: 'me' } }),
            );
          });
        });

        it('dispatches a LOAD_ME for "me"', () => {
          store.dispatch(action).then(() => {
            expect(store.getActions()).toContain(jasmine.objectContaining({ type: 'LOAD_ME', me: ME_DATA }));
          });
        });
      });

      describe('when the call fails', () => {
        beforeEach(() => {
          fetchMock.restore().getOnce('path:/me', new Promise((res, reject) => reject()));
        });

        it('dispatches a model error for "me"', () => {
          store.dispatch(action).then(() => {
            expect(store.getActions()).toContain(
              jasmine.objectContaining({ type: 'MODEL_STATUS_ERROR', model: { type: 'me' } }),
            );
          });
        });

        it('dispatches a blank LOAD_ME for an anonymous user', () => {
          store.dispatch(action).then(() => {
            expect(store.getActions()).toContain(jasmine.objectContaining({ type: 'LOAD_ME', me: {} }));
          });
        });
      });
    });
  });
});
