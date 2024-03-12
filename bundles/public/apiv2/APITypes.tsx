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

export type Event = {
  type: 'event';
  id: number;
  short: string;
  name: string;
  hashtag: string;
  date: string;
  timezone: string;
  paypalcurrency: string;
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
