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

export type Prize = {
  id: number;
  name: string;
  description?: string;
  minimumbid: string;
  sumdonations?: boolean;
  url?: string;
};

export type DonationAction =
  | {
      type: 'LOAD_DONATION';
      donation: Donation;
    }
  | {
      type: 'UPDATE_DONATION';
      fields: Partial<Donation>;
    }
  | {
      type: 'CREATE_BID';
      bid: Bid;
    }
  | {
      type: 'DELETE_BID';
      incentiveId: number;
    };
