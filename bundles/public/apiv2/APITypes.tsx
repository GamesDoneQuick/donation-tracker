export type DonationTransactionState = 'COMPLETED' | 'PENDING' | 'CANCELLED' | 'FLAGGED';
export type DonationDomain = 'PAYPAL' | 'LOCAL' | 'CHIPIN';
export type DonationReadState = 'PENDING' | 'READY' | 'IGNORED' | 'READ' | 'FLAGGED';
export type DonationCommentState = 'ABSENT' | 'PENDING' | 'DENIED' | 'APPROVED' | 'FLAGGED';

export type Donation = {
  type: 'donation';
  id: number;
  donor?: number;
  donor_name: string;
  event: number;
  domain: DonationDomain;
  transactionstate: DonationTransactionState;
  readstate: DonationReadState;
  commentstate: DonationCommentState;
  amount: number;
  currency: string;
  timereceived: string;
  comment?: string;
  commentlanguage: string;
  pinned: boolean;
  bids: DonationBid[];
  modcomment?: string;
};

export type DonationBid = {
  type: 'donationbid';
  id: number;
  donation: string;
  bid: string;
  amount: string;
  bid_name: string;
};

export type Event = {
  type: 'event';
  id: number;
  short: string;
  name: string;
  hashtag: string;
  date: string;
  timezone: string;
  use_one_step_screening: boolean;
  amount?: number;
  donation_count?: number;
};

export type Me = {
  username: string;
  superuser: boolean;
  staff: boolean;
  permissions: string[];
};
