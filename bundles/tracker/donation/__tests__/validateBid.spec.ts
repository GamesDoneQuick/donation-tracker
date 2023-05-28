import { Incentive } from '@tracker/event_details/EventDetailsTypes';

import { BID_MINIMUM_AMOUNT } from '../DonationConstants';
import { Bid, Donation } from '../DonationTypes';
import validateBid, { BidErrors } from '../validateBid';

const basicIncentive: Incentive = {
  id: 1,
  name: 'an incentive',
  amount: 0.0,
  parent: undefined,
  runname: 'the run',
  custom: false,
  order: 1,
  chain: false,
};

const incentiveWithOptions: Incentive = {
  id: 2,
  name: 'Pick a state',
  amount: 100.0,
  parent: undefined,
  runname: 'run #2',
  maxlength: 12,
  custom: false,
  description: 'idk i need an incentive',
  order: 2,
  chain: false,
};

const incentiveWithOptionsAsParent = {
  id: incentiveWithOptions.id,
  name: incentiveWithOptions.name,
  custom: incentiveWithOptions.custom!,
  maxlength: incentiveWithOptions.maxlength,
  description: incentiveWithOptions.description!,
};

const incentiveOption1: Incentive = {
  id: 3,
  name: 'virginia',
  parent: incentiveWithOptionsAsParent,
  amount: 50.0,
  runname: 'idk',
  order: 3,
  chain: false,
};

const donation: Donation = {
  name: '',
  email: '',
  amount: 75.0,
  comment: '',
  wantsEmails: 'CURR',
};

describe('validateBid', () => {
  it('passes with a complete basic bid', () => {
    const bid: Bid = {
      incentiveId: basicIncentive.id,
      amount: 2.5,
    };

    const validation = validateBid('USD', bid, basicIncentive, donation, [], false, false);
    expect(validation.valid).toBe(true);
    expect(validation.errors.length).toEqual(0);
  });

  describe('validating amount', () => {
    it('fails when amount is lower than allowed minimum', () => {
      const bid: Bid = {
        incentiveId: basicIncentive.id,
        amount: BID_MINIMUM_AMOUNT - 1,
        customoptionname: 'test',
      };

      const validation = validateBid('USD', bid, basicIncentive, donation, [], false, false);
      expect(validation.valid).toBe(false);
      expect(validation.errors).toContain({
        field: 'amount',
        message: BidErrors.AMOUNT_MINIMUM(BID_MINIMUM_AMOUNT, 'USD'),
      });
    });

    it('passes when amount equals allowed minimum', () => {
      const bid: Bid = {
        incentiveId: basicIncentive.id,
        amount: BID_MINIMUM_AMOUNT,
      };

      const validation = validateBid('USD', bid, basicIncentive, donation, [], false, false);
      expect(validation.valid).toBe(true);
      expect(validation.errors.length).toEqual(0);
    });

    it('passes when amount equals donation total', () => {
      const max = donation.amount!;
      const bid: Bid = {
        incentiveId: basicIncentive.id,
        amount: max,
      };

      const validation = validateBid('USD', bid, basicIncentive, donation, [], false, false);
      expect(validation.valid).toBe(true);
      expect(validation.errors.length).toEqual(0);
    });

    it('fails when amount exceeds donation total', () => {
      const max = donation.amount!;
      const bid: Bid = {
        incentiveId: basicIncentive.id,
        amount: max + 1,
      };

      const validation = validateBid('USD', bid, basicIncentive, donation, [], false, false);
      expect(validation.valid).toBe(false);
      expect(validation.errors).toContain({ field: 'amount', message: BidErrors.AMOUNT_MAXIMUM(max, 'USD') });
    });
  });

  describe('validating choice', () => {
    it('fails when no choice is selected', () => {
      const bid: Bid = {
        incentiveId: incentiveWithOptions.id,
        amount: 2.5,
      };

      const validation = validateBid('USD', bid, incentiveWithOptions, donation, [], true, false);
      expect(validation.valid).toBe(false);
      expect(validation.errors).toContain({ field: 'incentiveId', message: BidErrors.NO_CHOICE });
    });

    it('passes when an existing incentive choice is selected', () => {
      const bid: Bid = {
        incentiveId: incentiveOption1.id,
        amount: 2.5,
      };

      const validation = validateBid('USD', bid, incentiveWithOptions, donation, [], true, true);
      expect(validation.valid).toBe(true);
      expect(validation.errors.length).toEqual(0);
    });

    it('passes when a new incentive choice is given', () => {
      const bid: Bid = {
        incentiveId: incentiveOption1.id,
        amount: 2.5,
        customoptionname: 'test',
      };

      const validation = validateBid('USD', bid, incentiveWithOptions, donation, [], true, true, true);
      expect(validation.valid).toBe(true);
      expect(validation.errors.length).toEqual(0);
    });

    it('fails when a new incentive choice is selected but empty', () => {
      const bid: Bid = {
        incentiveId: incentiveOption1.id,
        amount: 2.5,
        customoptionname: '',
      };

      const validation = validateBid('USD', bid, incentiveWithOptions, donation, [], true, true, true);
      expect(validation.valid).toBe(false);
      expect(validation.errors).toContain({
        field: 'new option',
        message: BidErrors.NO_CUSTOM_CHOICE,
      });
    });

    it('fails when a new incentive choice is too long', () => {
      const bid: Bid = {
        incentiveId: incentiveOption1.id,
        amount: 2.5,
        customoptionname: 'this is too long to be allowable clearly',
      };

      const validation = validateBid('USD', bid, incentiveWithOptions, donation, [], true, true, true);
      expect(validation.valid).toBe(false);
      expect(validation.errors).toContain({
        field: 'new option',
        message: BidErrors.CUSTOM_CHOICE_LENGTH(incentiveWithOptions.maxlength!),
      });
    });
  });
});
