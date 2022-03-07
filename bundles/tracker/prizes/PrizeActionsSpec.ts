import fetchMock from 'fetch-mock';
import { AnyAction } from 'redux';
import configureMockStore from 'redux-mock-store';
import thunk, { ThunkDispatch } from 'redux-thunk';

import Endpoints from '@tracker/Endpoints';
import { StoreState } from '@tracker/Store';

import { fetchPrizes } from './PrizeActions';

type DispatchExts = ThunkDispatch<StoreState, void, AnyAction>;

const mockStore = configureMockStore<StoreState, DispatchExts>([thunk]);

describe('PrizeActions', () => {
  let store: ReturnType<typeof mockStore>;

  beforeEach(() => {
    store = mockStore();
    fetchMock.restore();
  });

  describe('#fetchPrizes', () => {
    it('works with a numeric event id', () => {
      fetchMock.getOnce(`${Endpoints.SEARCH}?event=1&type=prize`, 200);
      store.dispatch(fetchPrizes({ event: '1' }));
      expect(fetchMock.done()).toBe(true);
    });

    it('works with an event shortname', () => {
      fetchMock.getOnce(`${Endpoints.SEARCH}?eventshort=test&type=prize`, 200);
      store.dispatch(fetchPrizes({ event: 'test' }));
      expect(fetchMock.done()).toBe(true);
    });
  });
});
