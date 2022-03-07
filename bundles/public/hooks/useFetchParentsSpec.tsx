import React from 'react';
import { mount } from 'enzyme';
import fetchMock from 'fetch-mock';
import { Provider, useSelector } from 'react-redux';
import configureMockStore from 'redux-mock-store';
import thunk from 'redux-thunk';

import Endpoints from '@tracker/Endpoints';

import { useFetchParents } from './useFetchParents';

const mockStore = configureMockStore([thunk]);

function TestComponent() {
  const bids = useSelector((state: any) => state.models.bid);
  useFetchParents();
  return (
    <div>
      {bids?.map((bid: any) => (
        <div key={bid.pk}>{bid.public}</div>
      ))}
    </div>
  );
}

describe('useFetchParents', () => {
  let store: ReturnType<typeof mockStore>;

  beforeEach(() => {
    fetchMock.restore();
  });

  it('fetches missing parents', () => {
    fetchMock.getOnce(`${Endpoints.SEARCH}?ids=1%2C5&type=bid`, { body: [] });
    render({
      models: {
        bid: [
          {
            parent: 1,
            pk: 2,
          },
          {
            pk: 3,
          },
          {
            parent: 3,
            pk: 4,
          },
          {
            parent: 5,
            pk: 6,
          },
        ],
      },
    });
    expect(fetchMock.done()).toBe(true);
  });

  function render(storeState: any) {
    store = mockStore({
      models: { ...storeState.models },
      singletons: { ...storeState.singletons },
      status: { ...storeState.status },
    });
    return mount(
      <Provider store={store}>
        <TestComponent />
      </Provider>,
    );
  }
});
