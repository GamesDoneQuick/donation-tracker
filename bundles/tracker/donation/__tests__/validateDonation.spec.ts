import { DonationPost, DonationPostBid } from '@public/apiv2/APITypes';
import { processEvent } from '@public/apiv2/Processors';

import { getFixtureEvent } from '@spec/fixtures/event';

import validateDonation, { DonationErrors } from '../validateDonation';

const event = processEvent(getFixtureEvent());

function defaultPost(overrides?: Partial<DonationPost>): DonationPost {
  return {
    event: event.id,
    requested_alias: '',
    requested_email: '',
    amount: 50,
    comment: '',
    email_optin: false,
    bids: [],
    ...overrides,
  };
}

describe('validateDonation', () => {
  it('passes with a complete basic donation', () => {
    const validation = validateDonation(event, defaultPost(), 60000);
    expect(validation).toBeNull();
  });

  describe('validating amount', () => {
    it('fails when amount is empty', () => {
      const validation = validateDonation(event, { ...defaultPost(), amount: undefined }, 60000);
      expect(validation?.data).toEqual(jasmine.objectContaining({ amount: DonationErrors.NO_AMOUNT }));
    });

    it('fails when amount is lower than allowed minimum', () => {
      const validation = validateDonation(event, defaultPost({ amount: event.minimumdonation - 1 }), 60000);
      expect(validation?.data).toEqual(
        jasmine.objectContaining({
          amount: DonationErrors.AMOUNT_MINIMUM(event.minimumdonation, 'USD'),
        }),
      );
    });

    it('fails when amount is higher than allowed maximum', () => {
      const validation = validateDonation(event, defaultPost({ amount: 60001 }), 60000);
      expect(validation?.data).toEqual(
        jasmine.objectContaining({
          amount: DonationErrors.AMOUNT_MAXIMUM(60000, 'USD'),
        }),
      );
    });
  });

  describe('validating bids', () => {
    it('fails with bids total exceeding donation amount', () => {
      const validation = validateDonation(
        event,
        defaultPost({
          amount: 10,
          bids: Array(3).fill({
            id: 1,
            amount: 10,
          } satisfies DonationPostBid),
        }),
        60000,
      );
      expect(validation?.data).toEqual(
        jasmine.objectContaining({
          bids: DonationErrors.BID_SUM_EXCEEDS_TOTAL,
        }),
      );
    });

    it('fails with duplicate bid', () => {
      const validation = validateDonation(
        event,
        defaultPost({
          amount: 20,
          bids: Array(2).fill({
            id: 1,
            amount: 10,
          } satisfies DonationPostBid),
        }),
        60000,
      );
      expect(validation?.data).toEqual(
        jasmine.objectContaining({
          bids: DonationErrors.DUPLICATE_BID_ASSIGNMENT,
        }),
      );
    });

    it('fails with duplicate suggestion', () => {
      const validation = validateDonation(
        event,
        defaultPost({
          amount: 20,
          bids: Array(2).fill({
            parent: 1,
            name: 'foobar',
            amount: 10,
          } satisfies DonationPostBid),
        }),
        60000,
      );
      expect(validation?.data).toEqual(
        jasmine.objectContaining({
          bids: DonationErrors.DUPLICATE_BID_ASSIGNMENT,
        }),
      );
    });

    it('passes with two new suggestions on the same parent', () => {
      const validation = validateDonation(
        event,
        defaultPost({
          amount: 20,
          bids: [
            {
              parent: 1,
              name: 'foobar',
              amount: 10,
            },
            {
              parent: 1,
              name: 'barfoo',
              amount: 10,
            },
          ] satisfies DonationPostBid[],
        }),
        60000,
      );
      expect(validation).toBeNull();
    });

    it('passes with same suggestion on different parents', () => {
      const validation = validateDonation(
        event,
        defaultPost({
          amount: 20,
          bids: [
            {
              parent: 1,
              name: 'foobar',
              amount: 10,
            },
            {
              parent: 2,
              name: 'foobar',
              amount: 10,
            },
          ] satisfies DonationPostBid[],
        }),
        60000,
      );
      expect(validation).toBeNull();
    });

    it('passes with an existing bid and new suggestion', () => {
      const validation = validateDonation(
        event,
        defaultPost({
          amount: 20,
          bids: [
            {
              parent: 1,
              name: 'foobar',
              amount: 10,
            },
            {
              id: 2,
              amount: 10,
            },
          ] satisfies DonationPostBid[],
        }),
        60000,
      );
      expect(validation).toBeNull();
    });
  });

  describe('validating email', () => {
    it('fails with an invalid email address', () => {
      const validation = validateDonation(event, defaultPost({ requested_email: 'notavalidemail' }), 60000);
      expect(validation?.data).toEqual(
        jasmine.objectContaining({
          email: DonationErrors.INVALID_EMAIL,
        }),
      );
    });
  });
});
