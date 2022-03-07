import { createBid, deleteBid } from './DonationActions';
import DonationReducer from './DonationReducer';

describe('DonationReducer', () => {
  let state: ReturnType<typeof DonationReducer>;

  beforeEach(() => {
    state = DonationReducer(undefined, {
      type: 'LOAD_DONATION',
      donation: { name: '', email: '', amount: 50, comment: '', wantsEmails: 'CURR' },
      bids: [
        { amount: 5, customoptionname: '' },
        { incentiveId: 3, amount: 5, customoptionname: '' },
        { incentiveId: 4, amount: 5, customoptionname: '' },
      ],
      formErrors: { bidsform: [{ bid: ['Does not exist'] }], commentform: {} },
    });
  });

  describe('CREATE_BID', () => {
    it('clears out bid form errors and bids with no incentive ids', () => {
      state = DonationReducer(state, createBid({ incentiveId: 1, amount: 5, customoptionname: '' }));
      expect(state.bids).toHaveLength(3);
      expect(state.formErrors.bidsform).toHaveLength(0);
    });

    it('joins amounts together', () => {
      state = DonationReducer(state, createBid({ incentiveId: 1, amount: 5, customoptionname: '' }));
      state = DonationReducer(state, createBid({ incentiveId: 1, amount: 5, customoptionname: '' }));
      expect(state.bids).toHaveLength(3);
      expect(state.bids.find(bid => bid.incentiveId === 1)!.amount).toBe(10);
    });

    it('can add multiple bids', () => {
      state = DonationReducer(state, createBid({ incentiveId: 1, amount: 5, customoptionname: '' }));
      state = DonationReducer(state, createBid({ incentiveId: 2, amount: 5, customoptionname: '' }));
      expect(state.bids).toHaveLength(4);
    });
  });

  describe('DELETE_BID', () => {
    it('clears out bit form errors and bids with no incentive ids', () => {
      state = DonationReducer(state, deleteBid(3));
      expect(state.bids).toHaveLength(1);
      expect(state.formErrors.bidsform).toHaveLength(0);
    });
  });
});
