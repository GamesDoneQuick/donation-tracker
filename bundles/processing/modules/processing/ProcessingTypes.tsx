import { APIDonation as Donation } from '@public/apiv2/APITypes';

import { DonationState } from '../donations/DonationsStore';

export interface ProcessDefinition {
  donationState: DonationState;
  fetch: (eventId: number) => Promise<Donation[]>;
  action: (donationId: number) => Promise<Donation>;
  actionName: string;
  actionLabel: string;
}
