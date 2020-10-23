import fetchMock from 'fetch-mock';
import thunk from 'redux-thunk';
import configureMockStore from 'redux-mock-store';

import singletons from './singletons';
import Endpoints from '../../../tracker/Endpoints';

const mockStore = configureMockStore([thunk]);

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
        fetchMock.getOnce(Endpoints.ME, {
          body: { todos: ['do something'] },
          headers: { 'content-type': 'application/json' },
        });
      });

      it('dispatches a loading action for "me"', async () => {
        await store.dispatch(action).then(() => {
          expect(store.getActions()).toContain(jasmine.objectContaining({ type: 'MODEL_STATUS_LOADING', model: 'me' }));
        });
      });

      it('sends a request to the ME endpoint', async () => {
        await store.dispatch(action).then(() => {
          expect(fetchMock.done()).toBe(true);
        });
      });

      describe('when the call succeeds', () => {
        const ME_DATA = { username: 'jazzaboo' };
        beforeEach(() => {
          fetchMock.restore().getOnce(Endpoints.ME, {
            body: ME_DATA,
            headers: { 'content-type': 'application/json' },
          });
        });

        it('dispatches a model success for "me"', async () => {
          await store.dispatch(action).then(() => {
            expect(store.getActions()).toContain(
              jasmine.objectContaining({ type: 'MODEL_STATUS_SUCCESS', model: 'me' }),
            );
          });
        });

        it('dispatches a LOAD_ME for "me"', async () => {
          await store.dispatch(action).then(() => {
            expect(store.getActions()).toContain(jasmine.objectContaining({ type: 'LOAD_ME', me: ME_DATA }));
          });
        });
      });

      describe('when the call fails', () => {
        beforeEach(() => {
          fetchMock.restore().getOnce(Endpoints.ME, new Promise((res, reject) => reject()));
        });

        it('dispatches a model error for "me"', async () => {
          await store.dispatch(action).then(() => {
            expect(store.getActions()).toContain(jasmine.objectContaining({ type: 'MODEL_STATUS_ERROR', model: 'me' }));
          });
        });

        it('dispatches a blank LOAD_ME for an anonymous user', async () => {
          await store.dispatch(action).then(() => {
            expect(store.getActions()).toContain(jasmine.objectContaining({ type: 'LOAD_ME', me: {} }));
          });
        });
      });
    });
  });
});
