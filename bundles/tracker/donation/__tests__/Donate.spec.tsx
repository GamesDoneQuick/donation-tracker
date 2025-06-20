import React from 'react';
import MockAdapter from 'axios-mock-adapter';
import { Provider } from 'react-redux';
import { Route, Routes } from 'react-router';
import { StaticRouter } from 'react-router-dom/server';
import { act, fireEvent, render, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import Constants, { DefaultConstants } from '@common/Constants';
import Endpoints from '@public/apiv2/Endpoints';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { setRoot } from '@public/apiv2/reducers/apiRoot';
import { trackerApi } from '@public/apiv2/reducers/trackerApi';
import { store } from '@public/apiv2/Store';

import { getFixtureMixedBidsTree } from '@spec/fixtures/bid';
import { getFixturePagedEvent } from '@spec/fixtures/event';
import { waitForSpinner } from '@spec/helpers/rtl';

import Donate from '../components/Donate';

const eventId = 2;

const renderDonate = async () => {
  const rendered = render(
    <Constants.Provider value={{ ...DefaultConstants, PAYPAL_MAXIMUM_AMOUNT: 1000 }}>
      <Provider store={store}>
        <StaticRouter location={`/donate/${eventId}`}>
          <Routes>
            <Route path="/donate/:eventId" element={<Donate />} />
          </Routes>
        </StaticRouter>
      </Provider>
    </Constants.Provider>,
  );
  const getAddIncentivesButton = () => rendered.getByTestId('addincentives-button') as HTMLButtonElement;
  const getSubmitButton = () => rendered.getByTestId('donation-submit') as HTMLButtonElement;
  const getSubmitBidButton = () => rendered.getByTestId('incentiveBidForm-submitBid') as HTMLButtonElement;

  const fillField = async (fieldLabel: string | RegExp, value: string) => {
    const input = rendered.getByLabelText(fieldLabel);
    if (fieldLabel.toString().includes('amount')) {
      // ReactNumeric does not like fireEvent
      await act(() => userEvent.type(input, value));
    } else {
      await act(() => fireEvent.change(input, { target: value }));
    }
  };

  const addIncentive = async () => {
    const addButton = getAddIncentivesButton();
    await act(() => fireEvent.click(addButton));
  };

  const fillBid = async (incentiveId: string, bid: { choiceId?: string; amount?: number; custom?: string }) => {
    await act(() => fireEvent.click(rendered.getByTestId(`incentiveform-incentive-${incentiveId}`)));
    if (bid.amount != null) {
      await fillField(/Amount to put towards incentive/i, bid.amount.toString());
    }

    if (bid.custom != null) {
      await act(() => {
        const customOption = rendered.getByTestId('incentiveBidNewOption');
        fireEvent.click(customOption);
      });
      await act(() => {
        const customInput = rendered.getByTestId('incentiveBidCustomOption');
        fireEvent.change(customInput, { target: { value: bid.custom } });
      });
    }
  };

  const submitBid = async () => {
    const button = getSubmitBidButton();
    await act(() => fireEvent.click(button));
  };

  const removeBid = async (incentiveId: string) => {
    const button = rendered.getByTestId(`donationbid-remove-${incentiveId}`);
    await act(() => fireEvent.click(button));
  };

  await waitForSpinner(rendered);

  await waitFor(() => expect(rendered.findByLabelText('Email Address')).not.toBeNull());

  await waitForSpinner(rendered);

  return {
    ...rendered,
    getSubmitButton,
    getAddIncentivesButton,
    fillField,
    addIncentive,
    fillBid,
    submitBid,
    removeBid,
  };
};

describe('Donate', () => {
  let mock: MockAdapter;

  beforeAll(() => {
    mock = new MockAdapter(HTTPUtils.getInstance(), { onNoMatch: 'throwException' });
  });

  beforeEach(() => {
    store.dispatch(setRoot({ root: '//testserver/', limit: 500, csrfToken: 'deadbeef' }));
    store.dispatch(trackerApi.util.resetApiState());
    mock.reset();
    mock.onGet('//testserver/' + Endpoints.EVENTS).reply(() => [200, getFixturePagedEvent({ id: eventId })]);
    mock
      .onGet('//testserver/' + Endpoints.BIDS({ eventId: 2, feed: 'open', tree: true }))
      .reply(() => [200, getFixtureMixedBidsTree({})]);
  });

  afterAll(() => {
    mock.restore();
  });

  it('is not submittable by default', async () => {
    const { getSubmitButton } = await renderDonate();

    expect(getSubmitButton().disabled).toBe(true);
  });

  it('is submittable with just an amount set', async () => {
    const { getSubmitButton, fillField } = await renderDonate();
    await fillField(/amount/i, '10');

    expect(getSubmitButton().disabled).toBe(false);
  });

  it('is submittable with no alias set', async () => {
    const { getSubmitButton, fillField } = await renderDonate();
    await fillField(/email/i, 'someone@example.com');
    await fillField(/amount/i, '10');

    expect(getSubmitButton().disabled).toBe(false);
  });

  it('is submittable with all donation fields filled out', async () => {
    const { getSubmitButton, fillField } = await renderDonate();
    await fillField(/alias/i, 'my name');
    await fillField(/email/i, 'someone@example.com');
    await fillField(/amount/i, '10');
    await fillField(/comment/i, 'got a comment here');

    expect(getSubmitButton().disabled).toBe(false);
  });

  describe('adding incentives', () => {
    it('is disabled with no amount set', async () => {
      const { getAddIncentivesButton } = await renderDonate();
      expect(getAddIncentivesButton().disabled).toBe(true);
    });

    it('does not affect form submittability', async () => {
      const { addIncentive, getSubmitButton, fillField } = await renderDonate();
      await fillField(/amount/i, '10');
      await addIncentive();

      expect(getSubmitButton().disabled).toBe(false);
    });

    it('works with a valid bid', async () => {
      const { addIncentive, fillField, fillBid, getSubmitButton, submitBid } = await renderDonate();
      await fillField(/amount/i, '10');

      await addIncentive();
      await fillBid('121', { amount: 4.2 });
      await submitBid();

      expect(getSubmitButton().disabled).toBe(false);
    });

    it('works with a custom bid option', async () => {
      const { addIncentive, fillField, fillBid, getSubmitButton, submitBid } = await renderDonate();
      await fillField(/amount/i, '10');

      await addIncentive();
      await fillBid('122', { choiceId: '3', amount: 3.7, custom: 'idk' });
      await submitBid();

      expect(getSubmitButton().disabled).toBe(false);
    });

    it('can remove added bids', async () => {
      const { addIncentive, fillField, fillBid, getSubmitButton, submitBid, removeBid } = await renderDonate();
      await fillField(/amount/i, '10');

      await addIncentive();
      await fillBid('122', { choiceId: '3', amount: 3.7, custom: 'idk' });
      await submitBid();

      await removeBid('122-custom');

      expect(getSubmitButton().disabled).toBe(false);
    });
  });
});
