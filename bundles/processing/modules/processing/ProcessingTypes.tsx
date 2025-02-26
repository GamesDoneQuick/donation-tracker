import { UseDonationMutation } from '@public/apiv2/hooks';
import { DonationState } from '@public/apiv2/reducers/trackerApi';

export interface ProcessDefinition {
  donationState: DonationState;
  useAction: UseDonationMutation;
  actionName: string;
  actionLabel: string;
}
