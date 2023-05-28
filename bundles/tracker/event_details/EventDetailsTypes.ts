type Chain = {
  id: number;
  name: string;
  amount: number;
  goal: number;
};

export type Incentive = {
  id: number;
  name: string;
  customOption?: string;
  amount: number;
  chain: boolean;
  parent?: {
    id: number;
    name: string;
    custom: boolean;
    maxlength?: number;
    description?: string;
  };
  runname: string;
  order: number;
  count?: number;
  accepted_number?: number;
  goal?: number;
  chain_remaining?: number;
  chain_steps?: Chain[];
  description?: string;
  maxlength?: number;
  custom?: boolean;
};

export type Prize = {
  id: number;
  name: string;
  description?: string;
  minimumbid: string;
  sumdonations?: boolean;
  url?: string;
};

export type EventDetails = {
  currency: string;
  receiverName: string;
  receiverSolicitationText: string;
  receiverLogo: string;
  receiverPrivacyPolicy: string;
  prizesUrl: string;
  donateUrl: string;
  minimumDonation: number;
  maximumDonation: number;
  step: number;
  availableIncentives: { [incentiveId: number]: Incentive };
  prizes: Prize[];
};

export type EventDetailsAction =
  | { type: 'LOAD_EVENT_DETAILS'; eventDetails: EventDetails }
  | { type: 'LOAD_INCENTIVES'; incentives: Incentive[] };
