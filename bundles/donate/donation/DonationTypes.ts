export type Donation = {
  name?: string;
  nameVisibility: 'ALIAS' | 'ANON';
  email?: string;
  wantsEmails?: 'CURR' | 'OPTIN' | 'OPTOUT';
  amount?: number;
  comment?: string;
};

export type DonationAction =
  | {
      type: 'LOAD_DONATION';
      donation: Donation;
    }
  | {
      type: 'UPDATE_DONATION';
      fields: Partial<Donation>;
    };
