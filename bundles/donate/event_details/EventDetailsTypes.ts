export type EventDetails = {
  receiverName: string;
  prizesUrl: string;
  rulesUrl: string;
  donateUrl: string;
  minimumDonation: number;
  maximumDonation: number;
  step: number;
};

export type EventDetailsAction = { type: 'LOAD_EVENT_DETAILS'; eventDetails: EventDetails };
