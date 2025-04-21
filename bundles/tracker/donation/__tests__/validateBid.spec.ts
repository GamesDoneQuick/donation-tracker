import { DonationPost, DonationPostBid } from '@public/apiv2/APITypes';
import { processEvent } from '@public/apiv2/Processors';

import { getFixtureMixedBidsTree } from '@spec/fixtures/bid';
import { getFixtureEvent } from '@spec/fixtures/event';

import validateBid, { BidErrors } from '../validateBid';

const challenge = getFixtureMixedBidsTree().results.find(b => b.istarget)!;

const choice = getFixtureMixedBidsTree().results.find(b => !b.istarget)!;

const event = processEvent(getFixtureEvent());

const donation: DonationPost = {
  event: event.id,
  requested_alias: '',
  requested_email: '',
  amount: 50,
  comment: '',
  email_optin: false,
  bids: [],
};

describe('validateBid', () => {
  it('passes with a complete basic bid', () => {
    const bid: DonationPostBid = {
      id: challenge.id,
      amount: 1,
    };

    const validation = validateBid('USD', bid, challenge, donation, null);
    expect(validation).toBeNull();
  });

  describe('validating amount', () => {
    it('fails when amount is lower than allowed minimum', () => {
      const bid: DonationPostBid = {
        id: challenge.id,
        amount: 0.99,
      };

      const validation = validateBid('USD', bid, challenge, donation, null);
      expect(validation?.data).toEqual(
        jasmine.objectContaining({
          amount: BidErrors.AMOUNT_MINIMUM(1, 'USD'),
        }),
      );
    });

    it('passes when amount equals donation total', () => {
      const bid: DonationPostBid = {
        id: challenge.id,
        amount: donation.amount,
      };

      const validation = validateBid('USD', bid, challenge, donation, null);
      expect(validation).toBeNull();
    });

    it('fails when amount exceeds donation total', () => {
      const bid: DonationPostBid = {
        id: challenge.id,
        amount: donation.amount + 1,
      };

      const validation = validateBid('USD', bid, challenge, donation, null);
      expect(validation?.data).toEqual(
        jasmine.objectContaining({ amount: BidErrors.AMOUNT_MAXIMUM(donation.amount, 'USD') }),
      );
    });

    describe('validating choice', () => {
      it('passes when a new incentive choice is given', () => {
        const bid: DonationPostBid = {
          parent: choice.id,
          amount: 2.5,
          name: 'test',
        };

        const validation = validateBid('USD', bid, choice, donation, null);
        expect(validation).toBeNull();
      });

      it('fails when a new incentive choice is selected but empty', () => {
        const bid: DonationPostBid = {
          parent: choice.id,
          amount: 2.5,
          name: '',
        };

        const validation = validateBid('USD', bid, choice, donation, null);
        expect(validation?.data).toEqual(
          jasmine.objectContaining({
            new_option: BidErrors.NO_CUSTOM_CHOICE,
          }),
        );
      });

      it('fails when a new incentive choice is too long', () => {
        const bid: DonationPostBid = {
          parent: choice.id,
          amount: 2.5,
          name: 'this is too long to be allowable clearly',
        };

        const validation = validateBid('USD', bid, choice, donation, null);
        expect(validation?.data).toEqual(
          jasmine.objectContaining({
            new_option: BidErrors.CUSTOM_CHOICE_LENGTH(choice.option_max_length!),
          }),
        );
      });
    });
  });
});
