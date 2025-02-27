import * as React from 'react';
import { UseQueryResult } from 'react-query';

import { APIDonation } from '@public/apiv2/APITypes';
import { useDonationGroupsQuery } from '@public/apiv2/reducers/trackerApi';
import { useAppDispatch } from '@public/apiv2/Store';

import { GroupTabItem } from '@processing/modules/reading/ReadingTypes';

export function useGroupItems(donationsQuery: UseQueryResult<APIDonation[]>) {
  const groups = useDonationGroupsQuery();

  const groupItems = React.useMemo(
    () =>
      donationsQuery.data && groups.data
        ? [
            ...donationsQuery.data.reduce((groups, donation): Set<string> => {
              donation.groups?.forEach(g => groups.add(g));
              return groups;
            }, new Set<string>(groups.data)),
          ].map((group): GroupTabItem => ({ type: 'group', id: group }))
        : [],
    [donationsQuery.data, groups.data],
  );

  const dispatch = useAppDispatch();

  React.useEffect(() => {
    const existing = groupItems.map(g => g.id);
    const { data } = groups;
    if (data == null) {
      return;
    }
    // force a refetch if the donations include groups we don't know about
    if (existing.some(g => !data.includes(g))) {
      groups.refetch();
    }
  }, [dispatch, groupItems, groups]);

  return groupItems;
}
