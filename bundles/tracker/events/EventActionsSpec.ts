import fetchMock from 'fetch-mock';
import { AnyAction } from 'redux';
import configureMockStore from 'redux-mock-store';
import thunk, { ThunkDispatch } from 'redux-thunk';

import Endpoints from '@tracker/Endpoints';
import { StoreState } from '@tracker/Store';

import { fetchEvents } from './EventActions';

type DispatchExts = ThunkDispatch<StoreState, void, AnyAction>;

const mockStore = configureMockStore<StoreState, DispatchExts>([thunk]);

describe('EventActions', () => {
  let store: ReturnType<typeof mockStore>;

  beforeEach(() => {
    store = mockStore();
    fetchMock.restore();
  });

  describe('#fetchEvents', () => {
    it('works with a numeric id', () => {
      fetchMock.getOnce(`${Endpoints.SEARCH}?id=1&type=event`, 200);
      store.dispatch(fetchEvents({ id: '1' }));
      expect(fetchMock.done()).toBe(true);
    });

    it('works with a shortname', () => {
      fetchMock.getOnce(`${Endpoints.SEARCH}?short=test&type=event`, 200);
      store.dispatch(fetchEvents({ id: 'test' }));
      expect(fetchMock.done()).toBe(true);
    });
  });
});
