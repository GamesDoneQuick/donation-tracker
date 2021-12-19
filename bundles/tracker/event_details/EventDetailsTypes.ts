export type Incentive = {
  id: number;
  name: string;
  customOption?: string;
  amount: number;
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
  goal?: number;
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
  csrfToken: string;
  receiverName: string;
  receiverNotice: string;
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
