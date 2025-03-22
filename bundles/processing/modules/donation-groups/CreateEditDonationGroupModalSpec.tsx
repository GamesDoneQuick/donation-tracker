import React from 'react';
import MockAdapter from 'axios-mock-adapter';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Provider } from 'react-redux';
import { act, cleanup, fireEvent, render } from '@testing-library/react';

import { Me } from '@public/apiv2/APITypes';
import Endpoints from '@public/apiv2/Endpoints';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { apiRootSlice, trackerApi } from '@public/apiv2/reducers/trackerApi';
import { store } from '@public/apiv2/Store';

import CreateEditDonationGroupModal from '@processing/modules/donation-groups/CreateEditDonationGroupModal';

import { waitForSpinner } from '@spec/helpers/rtl';

describe('CreateEditDonationGroupModal', () => {
  let subject: ReturnType<typeof render>;
  let mock: MockAdapter;
  let me: Me;
  let createCode: number;
  let deleteCode: number;
  let closeSpy: jasmine.Spy;
  let queryClient: QueryClient;

  beforeAll(() => {
    mock = new MockAdapter(HTTPUtils.getInstance(), { onNoMatch: 'throwException' });
  });

  beforeEach(() => {
    store.dispatch(apiRootSlice.actions.setRoot({ root: '//testserver/', limit: 500, csrfToken: 'deadbeef' }));
    mock.reset();
    me = {
      username: 'test',
      staff: true,
      superuser: false,
      permissions: [],
    };
    closeSpy = jasmine.createSpy();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          refetchOnWindowFocus: false,
        },
      },
    });
    createCode = 201;
    deleteCode = 204;
    mock.onGet('//testserver/' + Endpoints.ME).reply(() => [200, me]);
    mock.onGet('//testserver/' + Endpoints.DONATION_GROUPS).reply(() => [200, ['foo', 'bar']]);
    mock
      .onPut(new RegExp('//testserver/' + Endpoints.DONATION_GROUP('([-\\w]+)')))
      .reply(config => [
        createCode,
        createCode < 300 ? /\/([-\w]+)\/$/.exec(config.url!)![1] : { error: 'Bad request' },
      ]);
    mock.onDelete(new RegExp('//testserver/' + Endpoints.DONATION_GROUP('([-\\w]+)'))).reply(() => [deleteCode, '']);
  });

  afterEach(async () => {
    await Promise.allSettled(store.dispatch(trackerApi.util.getRunningMutationsThunk()));
    cleanup();
  });

  afterAll(() => {
    mock.restore();
  });

  it('fetches groups on mount', async () => {
    await renderComponent();
    expect(trackerApi.util.selectCachedArgsForQuery(store.getState(), 'donationGroups')).toContain(undefined);
  });

  it('displays an error if the group to be created already would match the id', async () => {
    await renderComponent();
    act(() => {
      fireEvent.change(subject.getByTestId('group-name'), { target: { value: 'foo' } });
    });
    expect(subject.queryByText('Group ID already exists on the server.')).not.toBeNull();
  });

  it('creates a new group and closes modal on success', async () => {
    await renderComponent();
    await act(async () => {
      fireEvent.change(subject.getByTestId('group-name'), { target: { value: 'Foo Bar' } });
      fireEvent.click(subject.getByTestId('save-group'));
      const thunk = store.dispatch(trackerApi.util.getRunningMutationsThunk()).at(-1);
      expect(thunk?.arg.endpointName).toEqual('createDonationGroup');
      expect(thunk?.arg.originalArgs).toEqual('foo_bar');
      await thunk;
      expect(closeSpy).toHaveBeenCalled();
    });
  });

  it('displays error on error', async () => {
    createCode = 400;
    await renderComponent();
    await act(async () => {
      fireEvent.change(subject.getByTestId('group-name'), { target: { value: 'foobar' } });
      fireEvent.click(subject.getByTestId('save-group'));
    });
    await waitForSpinner(subject);
    expect(subject.getByText('Bad request')).not.toBeNull();
    expect(closeSpy).not.toHaveBeenCalled();
  });

  it('does not call to server on update', async () => {
    await renderComponent({ group: { id: 'foo', name: 'foo', color: 'accent', order: [] } });
    expect(subject.queryByTestId('delete-group')).toBeNull();
    await act(async () => {
      fireEvent.change(subject.getByTestId('group-name'), { target: { value: 'foo' } });
      const expected = store.dispatch(trackerApi.util.getRunningMutationsThunk()).length;
      fireEvent.click(subject.getByTestId('save-group'));
      expect(store.dispatch(trackerApi.util.getRunningMutationsThunk()).length).toEqual(expected);
      expect(closeSpy).toHaveBeenCalled();
    });
  });

  it('allows deletion of groups', async () => {
    me.permissions.push('tracker.delete_donationgroup');
    await renderComponent({ group: { id: 'foo', name: 'foo', color: 'accent', order: [] } });
    await act(async () => {
      await store.dispatch(trackerApi.endpoints.me.initiate());
    });
    await act(async () => {
      fireEvent.click(subject.getByTestId('delete-group'));
      const thunk = store.dispatch(trackerApi.util.getRunningMutationsThunk()).at(-1);
      expect(thunk?.arg.endpointName).toEqual('deleteDonationGroup');
      expect(thunk?.arg.originalArgs).toEqual('foo');
      await thunk;
      expect(closeSpy).toHaveBeenCalled();
    });
  });

  async function renderComponent(props?: Partial<React.ComponentProps<typeof CreateEditDonationGroupModal>>) {
    act(() => {
      store.dispatch(trackerApi.util.resetApiState());
    });
    cleanup();
    const defaultProps: React.ComponentProps<typeof CreateEditDonationGroupModal> = {
      onClose: closeSpy,
    };

    subject = render(
      <Provider store={store}>
        <QueryClientProvider client={queryClient}>
          <CreateEditDonationGroupModal {...defaultProps} {...props} />
        </QueryClientProvider>
      </Provider>,
    );

    await waitForSpinner(subject);
  }
});
