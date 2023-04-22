import { useDonationGroup } from '../donation-groups/DonationGroupsStore';
import { DonationState, useFilteredDonations } from '../donations/DonationsStore';
import { FilterGroupTabItem } from './ReadingTypes';

function useResolvedTabPredicate(tab: FilterGroupTabItem) {
  const group = useDonationGroup(tab.id);

  switch (tab.type) {
    case 'filter':
      return tab.predicate;
    case 'group':
      return group?.donationIds ?? [];
  }
}

export default function useDonationsForFilterGroupTab(tab: FilterGroupTabItem, donationState: DonationState) {
  const resolvedPredicate = useResolvedTabPredicate(tab);
  return useFilteredDonations(donationState, resolvedPredicate);
}
