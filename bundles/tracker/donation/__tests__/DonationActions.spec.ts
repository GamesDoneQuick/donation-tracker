import { buildDonationPayload } from '../DonationActions';
import { Donation } from '../DonationTypes';

describe('DonationActions', () => {
  describe('buildDonationPayload', () => {
    const csrfToken = 'something';

    const donation: Donation = {
      name: 'someone',
      email: 'email@example.com',
      wantsEmails: 'OPTOUT',
      amount: 20.0,
      comment: 'a comment',
    };

    const bids = [
      { incentiveId: 1, amount: 10.22 },
      { incentiveId: 2, amount: 3.52, customoptionname: 'a new choice' },
    ];

    it('converts donation field names to API fields', () => {
      const payload = buildDonationPayload(csrfToken, donation, []);

      expect(payload.requestedvisibility).toEqual('ALIAS');
      expect(payload.requestedalias).toEqual(donation.name);
      expect(payload.requestedemail).toEqual(donation.email);
      expect(payload.requestedsolicitemail).toEqual(donation.wantsEmails);
      expect(payload.amount).toEqual('20.00');
      expect(payload.comment).toEqual(donation.comment);
    });

    it('sends ANON for visibility when alias is blank', () => {
      const payload = buildDonationPayload(csrfToken, { ...donation, name: '' }, []);

      expect(payload.requestedvisibility).toEqual('ANON');
    });

    it('includes provided csrf token', () => {
      const payload = buildDonationPayload(csrfToken, donation, []);

      expect(payload.csrfmiddlewaretoken).toEqual(csrfToken);
    });

    it('converts bid fields to API fields', () => {
      const payload = buildDonationPayload(csrfToken, donation, bids);

      bids.forEach((bid, index) => {
        // TODO: this will go away when this isn't using django forms directly
        // @ts-ignore
        expect(payload[`bidsform-${index}-bid`]).toEqual(bid.incentiveId);
        // @ts-ignore
        expect(payload[`bidsform-${index}-customoptionname`]).toEqual(bid.customoptionname);
        // @ts-ignore
        expect(payload[`bidsform-${index}-amount`]).toEqual(bid.amount.toFixed(2));
      });
    });

    it('includes bid form meta fields', () => {
      const payload = buildDonationPayload(csrfToken, donation, bids);

      expect(payload['bidsform-TOTAL_FORMS']).toEqual(bids.length);
      expect(payload['bidsform-INITIAL_FORMS']).toEqual(0);
      expect(payload['bidsform-MIN_NUM_FORMS']).toEqual(0);
      expect(payload['bidsform-MAX_NUM_FORMS']).toEqual(10);
    });
  });
});
