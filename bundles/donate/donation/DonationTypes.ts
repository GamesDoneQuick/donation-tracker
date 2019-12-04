export type Bid = {
  incentiveId: number;
  amount: number;
  customoptionname?: string;
};

export type Donation = {
  name: string;
  nameVisibility: 'ALIAS' | 'ANON';
  email: string;
  wantsEmails: 'CURR' | 'OPTIN' | 'OPTOUT';
  amount?: number;
  comment: string;
};

export type Validation = {
  valid: boolean;
  errors: Array<{ field: string; message: string }>;
};

export type DonationAction =
  | { type: 'LOAD_DONATION'; donation: Donation; bids: Array<Bid>; formError?: string }
  | { type: 'UPDATE_DONATION'; fields: Partial<Donation> }
  | { type: 'CREATE_BID'; bid: Bid }
  | { type: 'DELETE_BID'; incentiveId: number };
