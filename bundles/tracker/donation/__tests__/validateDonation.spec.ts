import { MAX_BIDS_PER_DONATION } from '../DonationConstants';
import { Bid, Donation } from '../DonationTypes';
import validateDonation, { DonationErrors } from '../validateDonation';

const eventDetails = {
  csrfToken: 'testing',
  receiverName: 'a beneficiary',
  prizesUrl: 'https://example.com/prizes',
  donateUrl: 'https://example.com/donate',
  minimumDonation: 2.0,
  maximumDonation: 100.0,
  step: 0.1,
  availableIncentives: [],
  prizes: [],
};

describe('validateDonation', () => {
  it('passes with a complete basic donation', () => {
    const donation: Donation = {
      name: '',
      email: '',
      amount: 75.0,
      comment: '',
      wantsEmails: 'CURR',
    };

    const validation = validateDonation(eventDetails, donation, []);
    expect(validation.valid).toBe(true);
    expect(validation.errors.length).toEqual(0);
  });

  describe('validating amount', () => {
    it('fails when amount is empty', () => {
      const donation: Donation = {
        name: '',
        email: '',
        amount: undefined,
        comment: '',
        wantsEmails: 'CURR',
      };

      const validation = validateDonation(eventDetails, donation, []);
      expect(validation.valid).toBe(false);
      expect(validation.errors).toContain({ field: 'amount', message: DonationErrors.NO_AMOUNT });
    });

    it('fails when amount is lower than allowed minimum', () => {
      const donation: Donation = {
        name: '',
        email: '',
        amount: eventDetails.minimumDonation - 1,
        comment: '',
        wantsEmails: 'CURR',
      };

      const validation = validateDonation(eventDetails, donation, []);
      expect(validation.valid).toBe(false);
      expect(validation.errors).toContain({
        field: 'amount',
        message: DonationErrors.AMOUNT_MINIMUM(eventDetails.minimumDonation),
      });
    });

    it('fails when amount is higher than allowed maximum', () => {
      const donation: Donation = {
        name: '',
        email: '',
        amount: eventDetails.maximumDonation + 1,
        comment: '',
        wantsEmails: 'CURR',
      };

      const validation = validateDonation(eventDetails, donation, []);
      expect(validation.valid).toBe(false);
      expect(validation.errors).toContain({
        field: 'amount',
        message: DonationErrors.AMOUNT_MAXIMUM(eventDetails.maximumDonation),
      });
    });
  });

  describe('validating bids', () => {
    it('fails with more bids than are allowed', () => {
      const donation: Donation = {
        name: '',
        email: '',
        amount: eventDetails.minimumDonation + 1,
        comment: '',
        wantsEmails: 'CURR',
      };

      const bids: Bid[] = Array(MAX_BIDS_PER_DONATION + 1).fill({
        incentiveId: 1,
        amount: 2.0,
      });

      const validation = validateDonation(eventDetails, donation, bids);
      expect(validation.valid).toBe(false);
      expect(validation.errors).toContain({
        field: 'bids',
        message: DonationErrors.TOO_MANY_BIDS(MAX_BIDS_PER_DONATION),
      });
    });

    it('fails with bids total exceeding donation amount', () => {
      const donation: Donation = {
        name: '',
        email: '',
        amount: 10,
        comment: '',
        wantsEmails: 'CURR',
      };

      const bids: Bid[] = Array(3).fill({
        incentiveId: 1,
        amount: 10,
      });

      const validation = validateDonation(eventDetails, donation, bids);
      expect(validation.valid).toBe(false);
      expect(validation.errors).toContain({
        field: 'bids',
        message: DonationErrors.BID_SUM_EXCEEDS_TOTAL,
      });
    });
  });

  describe('validating email', () => {
    it('fails with an invalid email address', () => {
      const donation: Donation = {
        name: '',
        email: 'notavalidemail',
        amount: 10,
        comment: '',
        wantsEmails: 'CURR',
      };

      const validation = validateDonation(eventDetails, donation, []);
      expect(validation.valid).toBe(false);
      expect(validation.errors).toContain({
        field: 'email',
        message: DonationErrors.INVALID_EMAIL,
      });
    });
  });
});
