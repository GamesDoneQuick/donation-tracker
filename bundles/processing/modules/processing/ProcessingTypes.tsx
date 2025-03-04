import { Donation } from '@gamesdonequick/donation-tracker-api-types';

import { DonationState } from '../donations/DonationsStore';

export interface ProcessDefinition {
  donationState: DonationState;
  fetch: (eventId: number) => Promise<Donation[]>;
  action: (donationId: number) => Promise<Donation>;
  actionName: string;
  actionLabel: string;
}
