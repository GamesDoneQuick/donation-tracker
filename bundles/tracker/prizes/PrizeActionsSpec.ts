import fetchMock from 'fetch-mock';
import thunk, { ThunkDispatch } from 'redux-thunk';
import configureMockStore from 'redux-mock-store';
import Endpoints from '../Endpoints';
import { fetchPrizes } from './PrizeActions';
import { AnyAction } from 'redux';
import { StoreState } from '../Store';

type DispatchExts = ThunkDispatch<StoreState, void, AnyAction>;

const mockStore = configureMockStore<StoreState, DispatchExts>([thunk]);

describe('PrizeActions', () => {
  let store: ReturnType<typeof mockStore>;

  beforeEach(() => {
    store = mockStore();
  });

  describe('#fetchPrizes', () => {
    it('works with a numeric event id', () => {
      fetchMock.once(`${Endpoints.SEARCH}?event=1&type=prize`, 200);
      store.dispatch(fetchPrizes({ event: '1' }));
      expect(fetchMock.called()).toBe(true);
    });

    it('works with an event shortname', () => {
      fetchMock.once(`${Endpoints.SEARCH}?eventshort=test&type=prize`, 200);
      store.dispatch(fetchPrizes({ event: 'test' }));
      expect(fetchMock.called()).toBe(true);
    });
  });
});
