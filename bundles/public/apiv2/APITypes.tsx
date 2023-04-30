export type Donation = {
  type: 'donation';
  id: number;
  donor: string;
  donor_name: string;
  event: string;
  domain: string;
  transactionstate: string;
  readstate: string;
  commentstate: string;
  amount: string;
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

export type DonationProcessState =
  | 'unprocessed'
  | 'flagged'
  | 'ready'
  | 'read'
  | 'approved'
  | 'ignored'
  | 'denied'
  | 'unknown';

export type DonationProcessAction = {
  type: 'donationprocessaction';
  id: number;
  actor: User;
  donation?: Donation;
  donation_id: number;
  from_state: DonationProcessState;
  to_state: DonationProcessState;
  occurred_at: string;
  originating_action?: DonationProcessAction;
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
};

export type Me = {
  id: number;
  username: string;
  superuser: boolean;
  staff: boolean;
  permissions: string[];
};

export type User = {
  type: 'user';
  id: number;
  username: string;
};
