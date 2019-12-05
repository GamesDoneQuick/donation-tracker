import * as React from 'react';
import userEvent from '@testing-library/user-event';
import { createStore, fireEvent, render } from '../../testing/test-utils';

import { StoreState } from '../../Store';
import * as EventDetailsActions from '../../event_details/EventDetailsActions';
import DonationForm from '../components/DonationForm';
import * as DonationActions from '../DonationActions';
import { Bid } from '../DonationTypes';

const renderDonationForm = (store?: ReturnType<typeof createStore>) => {
  const rendered = render(<DonationForm csrfToken="something" />, { store });
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

describe('DonationForm', () => {
  it('is not submittable by default', () => {
    const { getSubmitButton } = renderDonationForm();

    expect(getSubmitButton().disabled).toBe(true);
  });

  it('is submittable with just an amount set', () => {
    const { getSubmitButton, fillField } = renderDonationForm();
    fillField(/amount/i, '10');

    expect(getSubmitButton().disabled).toBe(false);
  });

  it('is submittable with no alias set', () => {
    const { getSubmitButton, fillField } = renderDonationForm();
    fillField(/email/i, 'someone@example.com');
    fillField(/amount/i, '10');

    expect(getSubmitButton().disabled).toBe(false);
  });

  it('is submittable with all donation fields filled out', () => {
    const { getSubmitButton, fillField } = renderDonationForm();
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
          { id: 1, name: 'an incentive', amount: 0, runname: 'some run' },
          { id: 2, name: 'an incentive with children', amount: 0, runname: 'some run', custom: true },
          { id: 3, name: 'child 1', parent: { id: 2, name: 'parent', custom: true }, amount: 0, runname: 'some run' },
          { id: 4, name: 'child 2', parent: { id: 2, name: 'parent', custom: true }, amount: 0, runname: 'some run' },
        ]),
      );

      return store;
    };

    it('is disabled with no amount set', () => {
      const { getAddIncentivesButton } = renderDonationForm();
      expect(getAddIncentivesButton().disabled).toBe(true);
    });

    it('does not affect form submittability', () => {
      const store = createStore();
      const { addIncentive, getSubmitButton, fillField } = renderDonationForm(store);
      fillField(/amount/i, '10');

      expect(getSubmitButton().disabled).toBe(false);
    });

    it('works with a valid bid', () => {
      const store = createStoreWithIncentives();
      const { addIncentive, fillField, fillBid, getSubmitButton, submitBid } = renderDonationForm(store);
      fillField(/amount/i, '10');

      addIncentive();
      fillBid('1', { amount: 4.2 });
      submitBid();

      expect(getSubmitButton().disabled).toBe(false);
    });

    it('works with a custom bid option', () => {
      const store = createStoreWithIncentives();
      const { addIncentive, fillField, fillBid, getSubmitButton, submitBid } = renderDonationForm(store);
      fillField(/amount/i, '10');

      addIncentive();
      fillBid('2', { choiceId: '3', amount: 3.7, custom: 'idk' });
      submitBid();

      expect(getSubmitButton().disabled).toBe(false);
    });

    it('can remove added bids', () => {
      const store = createStoreWithIncentives();
      const { addIncentive, fillField, fillBid, getSubmitButton, submitBid, removeBid } = renderDonationForm(store);
      fillField(/amount/i, '10');

      addIncentive();
      fillBid('2', { choiceId: '3', amount: 3.7, custom: 'idk' });
      submitBid();

      removeBid('2');

      expect(getSubmitButton().disabled).toBe(false);
    });
  });
});
