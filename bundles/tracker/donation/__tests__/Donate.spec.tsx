import * as React from 'react';
import { MemoryRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';

import * as EventDetailsActions from '@tracker/event_details/EventDetailsActions';
import { createStore, fireEvent, render } from '@tracker/testing/test-utils';

import Donate from '../components/Donate';

const renderDonate = (store?: ReturnType<typeof createStore>) => {
  const rendered = render(
    <MemoryRouter>
      <Donate eventId="some-event" />
    </MemoryRouter>,
    { store },
  );
  const getAddIncentivesButton = () => rendered.getByTestId('addincentives-button') as HTMLButtonElement;
  const getSubmitButton = () => rendered.getByTestId('donation-submit') as HTMLButtonElement;
  const getSubmitBidButton = () => rendered.getByTestId('incentiveBidForm-submitBid') as HTMLButtonElement;

  const fillField = (fieldLabel: string | RegExp, value: string) => {
    const input = rendered.getByLabelText(fieldLabel);
    userEvent.type(input, value);
  };

  const addIncentive = () => {
    const addButton = getAddIncentivesButton();
    fireEvent.click(addButton);
  };

  const fillBid = (incentiveId: string, bid: { choiceId?: string; amount?: number; custom?: string }) => {
    fireEvent.click(rendered.getByTestId(`incentiveform-incentive-${incentiveId}`));
    if (bid.amount != null) {
      fillField(/Amount to put towards incentive/i, bid.amount.toString());
    }

    if (bid.custom != null) {
      const customOption = rendered.getByTestId('incentiveBidNewOption');
      fireEvent.click(customOption);
      const customInput = rendered.getByTestId('incentiveBidCustomOption');
      userEvent.type(customInput, bid.custom);
    }
  };

  const submitBid = () => {
    const button = getSubmitBidButton();
    fireEvent.click(button);
  };

  const removeBid = (incentiveId: string) => {
    const button = rendered.getByTestId(`donationbid-remove-${incentiveId}`);
    fireEvent.click(button);
  };

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
  it('is not submittable by default', () => {
    const { getSubmitButton } = renderDonate();

    expect(getSubmitButton().disabled).toBe(true);
  });

  it('is submittable with just an amount set', () => {
    const { getSubmitButton, fillField } = renderDonate();
    fillField(/amount/i, '10');

    expect(getSubmitButton().disabled).toBe(false);
  });

  it('is submittable with no alias set', () => {
    const { getSubmitButton, fillField } = renderDonate();
    fillField(/email/i, 'someone@example.com');
    fillField(/amount/i, '10');

    expect(getSubmitButton().disabled).toBe(false);
  });

  it('is submittable with all donation fields filled out', () => {
    const { getSubmitButton, fillField } = renderDonate();
    fillField(/alias/i, 'my name');
    fillField(/email/i, 'someone@example.com');
    fillField(/amount/i, '10');
    fillField(/comment/i, 'got a comment here');

    expect(getSubmitButton().disabled).toBe(false);
  });

  describe('adding incentives', () => {
    const createStoreWithIncentives = () => {
      const store = createStore();
      store.dispatch(
        EventDetailsActions.loadIncentives([
          { id: 1, name: 'an incentive', amount: 0, runname: 'some run', order: 1, chain: false },
          {
            id: 2,
            name: 'an incentive with children',
            amount: 0,
            runname: 'some run',
            custom: true,
            order: 1,
            chain: false,
          },
          {
            id: 3,
            name: 'child 1',
            parent: { id: 2, name: 'parent', custom: true },
            amount: 0,
            runname: 'some run',
            order: 1,
            chain: false,
          },
          {
            id: 4,
            name: 'child 2',
            parent: { id: 2, name: 'parent', custom: true },
            amount: 0,
            runname: 'some run',
            order: 1,
            chain: false,
          },
        ]),
      );

      return store;
    };

    it('is disabled with no amount set', () => {
      const { getAddIncentivesButton } = renderDonate();
      expect(getAddIncentivesButton().disabled).toBe(true);
    });

    it('does not affect form submittability', () => {
      const store = createStore();
      const { addIncentive, getSubmitButton, fillField } = renderDonate(store);
      fillField(/amount/i, '10');
      addIncentive();

      expect(getSubmitButton().disabled).toBe(false);
    });

    it('works with a valid bid', () => {
      const store = createStoreWithIncentives();
      const { addIncentive, fillField, fillBid, getSubmitButton, submitBid } = renderDonate(store);
      fillField(/amount/i, '10');

      addIncentive();
      fillBid('1', { amount: 4.2 });
      submitBid();

      expect(getSubmitButton().disabled).toBe(false);
    });

    it('works with a custom bid option', () => {
      const store = createStoreWithIncentives();
      const { addIncentive, fillField, fillBid, getSubmitButton, submitBid } = renderDonate(store);
      fillField(/amount/i, '10');

      addIncentive();
      fillBid('2', { choiceId: '3', amount: 3.7, custom: 'idk' });
      submitBid();

      expect(getSubmitButton().disabled).toBe(false);
    });

    it('can remove added bids', () => {
      const store = createStoreWithIncentives();
      const { addIncentive, fillField, fillBid, getSubmitButton, submitBid, removeBid } = renderDonate(store);
      fillField(/amount/i, '10');

      addIncentive();
      fillBid('2', { choiceId: '3', amount: 3.7, custom: 'idk' });
      submitBid();

      removeBid('2');

      expect(getSubmitButton().disabled).toBe(false);
    });
  });
});
