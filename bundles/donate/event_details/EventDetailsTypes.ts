export type Incentive = {
  id: number;
  name: string;
  customOption?: string;
  amount: number;
  parent?: {
    id: number;
    name: string;
    custom: boolean;
    maxlength: number;
    description: string;
  };
  runname: string;
  count?: number;
  goal?: number;
  description?: string;
  maxlength?: number;
  custom?: boolean;
};

export type EventDetails = {
  receiverName: string;
  prizesUrl: string;
  rulesUrl: string;
  donateUrl: string;
  minimumDonation: number;
  maximumDonation: number;
  step: number;
  availableIncentives: { [incentiveId: number]: Incentive };
};

export type EventDetailsAction = { type: 'LOAD_EVENT_DETAILS'; eventDetails: EventDetails };
