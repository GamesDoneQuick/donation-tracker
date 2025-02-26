import * as React from 'react';

import { useDonationGroupsQuery } from '@public/apiv2/hooks';
import { Donation } from '@public/apiv2/Models';

import useDonationGroupsStore from '@processing/modules/donation-groups/DonationGroupsStore';
import { GroupTabItem } from '@processing/modules/reading/ReadingTypes';

export function useGroupItems(donations?: Donation[]) {
  const { data: groups, refetch } = useDonationGroupsQuery({ listen: true });
  const { syncDonationGroupsWithServer } = useDonationGroupsStore();

  const groupItems = React.useMemo(
    () => (groups ?? []).map((group): GroupTabItem => ({ type: 'group', id: group })),
    [groups],
  );

  React.useEffect(() => {
    if (groups) {
      syncDonationGroupsWithServer(groups);
    }
  }, [groups, syncDonationGroupsWithServer]);

  React.useEffect(() => {
    if (groups == null) {
      return;
    }
    // force a refetch if the donations include groups we don't know about
    // shouldn't ever happen in practice if the socket is working properly
    if (donations?.some(d => d.groups?.some(dg => !groups.includes(dg)))) {
      refetch();
    }
  }, [donations, groups, refetch]);

  return groupItems;
}
