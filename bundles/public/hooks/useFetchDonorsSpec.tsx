import React from 'react';
import { Provider, useSelector } from 'react-redux';
import { mount } from 'enzyme';
import fetchMock from 'fetch-mock';
import configureMockStore from 'redux-mock-store';
import thunk from 'redux-thunk';
import { useFetchDonors } from './useFetchDonors';
import Endpoints from '../../tracker/Endpoints';

const mockStore = configureMockStore([thunk]);

function TestComponent({ eventId }: { eventId: number }) {
  const donors = useSelector((state: any) => state.models.donors);
  useFetchDonors(eventId);
  return (
    <div>
      {donors?.map((d: any) => (
        <div key={d.pk}>{d.public}</div>
      ))}
    </div>
  );
}

describe('useFetchDonors', () => {
  let store: ReturnType<typeof mockStore>;
  const eventId = 1;

  beforeEach(() => {
    fetchMock.restore();
  });

  it('fetches donors by event if donors are completely missing', () => {
    fetchMock.getOnce(`${Endpoints.SEARCH}?event=${eventId}&type=donor`, { body: [] });
    render({});
    expect(fetchMock.done()).toBe(true);
  });

  it('fetches missing non-anonymous donors when donors already exist', () => {
    fetchMock.getOnce(`${Endpoints.SEARCH}?ids=1%2C3&type=donor`, { body: [] });
    render({
      models: {
        donor: [{ pk: 2 }],
        donation: [
          {
            donor: 1,
            donor__visibility: 'ALIAS',
          },
          {
            donor: 2,
            donor__visibility: 'ALIAS',
          },
          {
            donor: 3,
            donor__visibility: 'ALIAS',
          },
          {
            donor: 4,
            donor__visibility: 'ANON',
          },
        ],
      },
    });
    expect(fetchMock.done()).toBe(true);
  });

  it('fetches nothing when no non-anonymous donors are missing', () => {
    fetchMock.get('*', 404);
    render({
      models: {
        donor: [{ pk: 2 }],
        donation: [
          {
            donor: 1,
            donor__visibility: 'ANON',
          },
          {
            donor: 2,
            donor__visibility: 'ALIAS',
          },
        ],
      },
    });
    expect(fetchMock.calls().length).toBe(0);
  });

  function render(storeState: any) {
    store = mockStore({
      models: { ...storeState.models },
      singletons: { ...storeState.singletons },
      status: { ...storeState.status },
    });
    return mount(
      <Provider store={store}>
        <TestComponent eventId={eventId} />
      </Provider>,
    );
  }
});
