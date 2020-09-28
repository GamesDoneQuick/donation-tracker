import fetchMock from 'fetch-mock';
import { fetchEvents } from './EventActions';
import { AnyAction } from 'redux';
import thunk, { ThunkDispatch } from 'redux-thunk';
import configureMockStore from 'redux-mock-store';
import { ExtraArguments, StoreState } from '../Store';

type DispatchExts = ThunkDispatch<StoreState, ExtraArguments, AnyAction>;

const mockStore = configureMockStore<StoreState, DispatchExts>([
  thunk.withExtraArgument({ apiRoot: 'http://testserver/' }),
]);

describe('EventActions', () => {
  let store: ReturnType<typeof mockStore>;

  beforeEach(() => {
    store = mockStore();
    fetchMock.restore();
  });

  describe('#fetchEvents', () => {
    it('works with a numeric id', () => {
      fetchMock.getOnce('path:/search/', 200, { query: { id: '1', type: 'event' } });
      store.dispatch(fetchEvents({ id: '1' }));
      expect(fetchMock.done()).toBe(true);
    });

    it('works with a shortname', () => {
      fetchMock.getOnce('path:/search/', 200, { query: { short: 'test', type: 'event' } });
      store.dispatch(fetchEvents({ id: 'test' }));
      expect(fetchMock.called()).toBe(true);
    });
  });
});
