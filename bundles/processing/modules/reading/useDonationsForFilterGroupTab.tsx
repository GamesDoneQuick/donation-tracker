import { useFilteredDonations } from '@public/apiv2/hooks';
import { DonationState } from '@public/apiv2/reducers/trackerApi';

import { useDonationGroup } from '../donation-groups/DonationGroupsStore';
import { FilterGroupTabItem } from './ReadingTypes';

function useResolvedTabPredicate(tab: FilterGroupTabItem) {
  const group = useDonationGroup(tab.id);

  switch (tab.type) {
    case 'filter':
      return tab.predicate;
    case 'group':
      return group?.id || '';
  }
}

export default function useDonationsForFilterGroupTab(tab: FilterGroupTabItem, donationState: DonationState) {
  const resolvedPredicate = useResolvedTabPredicate(tab);
  return useFilteredDonations(donationState, resolvedPredicate);
}
