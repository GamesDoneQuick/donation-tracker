import fetchMock from 'fetch-mock';
import configureMockStore from 'redux-mock-store';
import thunk from 'redux-thunk';

import Endpoints from '@tracker/Endpoints';
import { SafeDispatch } from '@tracker/hooks/useDispatch';
import { StoreState } from '@tracker/Store';

import { fetchPrizes } from './PrizeActions';

const mockStore = configureMockStore<StoreState, SafeDispatch>([thunk]);

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
