import type { Donation } from '@gamesdonequick/donation-tracker-api-types';

import { DonationGroupColor } from '../donation-groups/DonationGroupsStore';

export interface FilterGroupTabItemBase {
  type: 'filter' | 'group';
  id: string;
}

export interface FilterTabItem extends FilterGroupTabItemBase {
  type: 'filter';
  label: string;
  color: DonationGroupColor;
  predicate: (donation: Donation) => boolean;
}

export interface GroupTabItem extends FilterGroupTabItemBase {
  type: 'group';
}

export type FilterGroupTabItem = FilterTabItem | GroupTabItem;

export const FILTER_ITEMS: FilterTabItem[] = [
  {
    type: 'filter',
    id: 'all',
    label: 'All Donations',
    color: 'default',
    predicate: () => true,
  },
  {
    type: 'filter',
    id: 'no-comment',
    label: 'No Comment',
    color: 'default',
    predicate: donation => donation.comment == null || donation.comment.length === 0,
  },
  {
    type: 'filter',
    id: 'anonymous',
    label: 'Anonymous',
    color: 'default',
    // TODO(faulty): Better represent anonymous donations so they actually have a
    // flag instead of having to check the name like this.
    predicate: donation => donation.donor_name === '(Anonymous)' || donation.donor_name === '',
  },
  {
    type: 'filter',
    id: 'pinned',
    label: 'Pinned',
    color: 'default',
    predicate: donation => donation.pinned,
  },
];
