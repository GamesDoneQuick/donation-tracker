import { APIDonation as Donation } from '@public/apiv2/APITypes';

import { DonationState } from '../donations/DonationsStore';

export interface ProcessDefinition {
  donationState: DonationState;
  fetch: (eventId: string) => Promise<Donation[]>;
  action: (donationId: string) => Promise<Donation>;
  actionName: string;
  actionLabel: string;
}
