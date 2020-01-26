export type Bid = {
  incentiveId?: number;
  amount: number;
  customoptionname?: string;
};

export type Donation = {
  name: string;
  email: string;
  wantsEmails: 'CURR' | 'OPTIN' | 'OPTOUT';
  amount?: number;
  comment: string;
};

type ValidationError = { field: string; message: string };

export type Validation = {
  valid: boolean;
  errors: ValidationError[];
};

export type FormError = { message: string; code?: string } | string;

export type BidFormErrors = {
  bid?: FormError[];
  customoptionname?: FormError[];
  amount?: FormError[];
};

export type CommentFormErrors = {
  __all__?: FormError[];
  requestedalias?: FormError[];
  requestedemail?: FormError[];
  requestedsolicitemail?: FormError[];
  requestedvisibility?: FormError[];
  amount?: FormError[];
  comment?: FormError[];
};

export type DonationFormErrors = {
  bidsform: BidFormErrors[];
  commentform: CommentFormErrors;
};

export type DonationAction =
  | { type: 'LOAD_DONATION'; donation: Donation; bids: Bid[]; formErrors: DonationFormErrors }
  | { type: 'UPDATE_DONATION'; fields: Partial<Donation> }
  | { type: 'CREATE_BID'; bid: Bid }
  | { type: 'DELETE_BID'; incentiveId: number };
