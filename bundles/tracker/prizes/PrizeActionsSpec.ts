import fetchMock from 'fetch-mock';
import thunk, { ThunkDispatch } from 'redux-thunk';
import configureMockStore from 'redux-mock-store';
import { fetchPrizes } from './PrizeActions';
import { AnyAction } from 'redux';
import { ExtraArguments, StoreState } from '../Store';

type DispatchExts = ThunkDispatch<StoreState, ExtraArguments, AnyAction>;

const mockStore = configureMockStore<StoreState, DispatchExts>([
  thunk.withExtraArgument({ apiRoot: 'http://testserver/' }),
]);

describe('PrizeActions', () => {
  let store: ReturnType<typeof mockStore>;

  beforeEach(() => {
    store = mockStore();
    fetchMock.restore();
  });

  describe('#fetchPrizes', () => {
    it('works with a numeric event id', () => {
      fetchMock.getOnce('path:/search/', 200, { query: { event: '1', type: 'prize' } });
      store.dispatch(fetchPrizes({ event: '1' }));
      expect(fetchMock.done()).toBe(true);
    });

    it('works with an event shortname', () => {
      fetchMock.getOnce('path:/search/', 200, { query: { eventshort: 'test', type: 'prize' } });
      store.dispatch(fetchPrizes({ event: 'test' }));
      expect(fetchMock.done()).toBe(true);
    });
  });
});
