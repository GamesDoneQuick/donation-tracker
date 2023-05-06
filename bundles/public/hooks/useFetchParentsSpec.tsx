import React from 'react';
import MockAdapter from 'axios-mock-adapter';
import { Provider, useSelector } from 'react-redux';
import configureMockStore from 'redux-mock-store';
import thunk from 'redux-thunk';
import { render, waitFor } from '@testing-library/react';

import Endpoints from '@public/apiv2/Endpoints';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { Bid, findParent } from '@public/apiv2/Models';

import { useFetchParents } from './useFetchParents';

const mockStore = configureMockStore([thunk]);

function TestComponent() {
  const bids = useSelector((state: any) => state.models.bid) as Bid[];
  const { loading, failed } = useFetchParents();

  function parentName(bid: Bid) {
    const parent = findParent(bids, bid);
    if (parent) {
      return parent.name;
    }
    if (loading) {
      return 'fetching...';
    }
    if (failed) {
      return 'failed!';
    }
    return 'unknown';
  }

  return (
    <div>
      {bids?.map(bid => (
        <div key={bid.id}>
          {bid.name} {parentName(bid)}
        </div>
      ))}
    </div>
  );
}

describe('useFetchParents', () => {
  let store: ReturnType<typeof mockStore>;
  let subject: ReturnType<typeof renderComponent>;
  let mock: MockAdapter;

  beforeAll(() => {
    mock = new MockAdapter(HTTPUtils.getInstance(), { onNoMatch: 'throwException' });
  });

  beforeEach(() => {
    mock.reset();
  });

  afterAll(() => {
    mock.restore();
  });

  it('fetches missing parents', async () => {
    mock.onGet(Endpoints.BIDS(), { params: { id: [1, 5] } }).replyOnce(200, { results: [{ id: 1 }, { id: 5 }] });
    subject = renderComponent({
      models: {
        bid: [
          {
            parent: 1,
            id: 2,
          },
          {
            id: 3,
          },
          {
            parent: 3,
            id: 4,
          },
          {
            parent: 5,
            id: 6,
          },
        ],
      },
    });
    expect(mock.history.get.length).toEqual(1);
    // all the parents have blank names
    await waitFor(() => expect(subject.getAllByText('unknown').length).toEqual(3));
  });

  it('returns an error on failure', async () => {
    // fake an error by not setting up a mock response
    subject = renderComponent({
      models: {
        bid: [
          {
            parent: 1,
            id: 2,
          },
        ],
      },
    });
    await waitFor(() => expect(subject.getAllByText('failed!').length).toEqual(1));
  });

  function renderComponent(storeState: any) {
    store = mockStore({
      models: { ...storeState.models },
      singletons: { ...storeState.singletons },
      status: { ...storeState.status },
    });
    return render(
      <Provider store={store}>
        <TestComponent />
      </Provider>,
    );
  }
});
