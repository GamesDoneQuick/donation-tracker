import * as React from 'react';
import configureMockStore from 'redux-mock-store';
import thunk from 'redux-thunk';
import { mount } from 'enzyme';
import { Provider } from 'react-redux';
import fetchMock from 'fetch-mock';

import ScheduleEditor from './index';

const mockStore = configureMockStore([thunk]);

describe('ScheduleEditor', () => {
  let store: ReturnType<typeof mockStore>;
  let subject: ReturnType<typeof render>;
  const eventId = 1;

  beforeEach(() => {
    fetchMock.restore();
    fetchMock.get('*', 404);
  });

  it('shows an error if things fail to load', () => {
    subject = render({ status: { speedrun: 'error', event: 'error', me: 'error' } });
    expect(subject.text()).toContain('Failed to fetch speedruns');
  });

  function render(storeState: any) {
    store = mockStore({
      models: { ...storeState.models },
      singletons: { ...storeState.singletons },
      status: { ...storeState.status },
    });
    return mount(
      <Provider store={store}>
        <ScheduleEditor match={{ params: { event: eventId } }} />
      </Provider>,
    );
  }
});
