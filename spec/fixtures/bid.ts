import { FlatBid, PaginationInfo, TreeBid } from '@public/apiv2/APITypes';

import { Incentive } from '@tracker/event_details/EventDetailsTypes';

export function getFixtureBid(overrides?: Partial<Incentive>): Incentive {
  return {
    id: 1,
    name: 'Test Incentive',
    amount: 0,
    runname: 'Test Run',
    order: 1,
    ...overrides,
  };
}

export function getFixturePendingBidFlat(
  parentOverrides?: Omit<Partial<FlatBid>, 'level' | 'parent'>,
  childOverrides?: Omit<Partial<FlatBid>, 'level' | 'parent'>,
): PaginationInfo<FlatBid> {
  const parentId = parentOverrides?.id ?? 122;
  return {
    count: 2,
    previous: null,
    next: null,
    results: [
      {
        id: parentId,
        level: 0,
        parent: null,
        type: 'bid',
        bid_type: 'choice',
        name: 'Naming Incentive',
        speedrun: null,
        state: 'OPENED',
        description: 'Name the Character',
        shortdescription: '',
        estimate: null,
        close_at: null,
        post_run: false,
        goal: null,
        chain: false,
        total: 50,
        count: 2,
        istarget: false,
        revealedtime: null,
        allowuseroptions: true,
        option_max_length: 12,
        ...parentOverrides,
      },
      {
        id: 123,
        type: 'bid',
        level: 1,
        goal: null,
        speedrun: null,
        close_at: null,
        post_run: false,
        chain: false,
        parent: parentId,
        bid_type: 'option',
        name: 'Unapproved',
        description: '',
        shortdescription: '',
        estimate: null,
        istarget: true,
        revealedtime: null,
        state: 'PENDING',
        total: 20,
        count: 1,
        ...childOverrides,
      },
    ],
  };
}

export function getFixturePendingBidTree(
  parentOverrides?: Partial<TreeBid>,
  childOverrides?: Partial<Omit<NonNullable<TreeBid['options']>[0], 'state'>>,
): PaginationInfo<TreeBid> {
  return {
    count: 1,
    previous: null,
    next: null,
    results: [
      {
        id: 122,
        type: 'bid',
        bid_type: 'choice',
        name: 'Naming Incentive',
        speedrun: null,
        state: 'OPENED',
        description: 'Name the Character',
        shortdescription: '',
        estimate: null,
        close_at: null,
        post_run: false,
        goal: null,
        chain: false,
        total: 50,
        count: 2,
        istarget: false,
        revealedtime: null,
        allowuseroptions: true,
        option_max_length: 12,
        options: [
          {
            id: 123,
            type: 'bid',
            bid_type: 'option',
            name: 'Unapproved',
            description: '',
            shortdescription: '',
            estimate: null,
            istarget: true,
            revealedtime: null,
            state: 'PENDING',
            total: 20,
            count: 1,
            ...childOverrides,
          },
        ],
        ...parentOverrides,
      },
    ],
  };
}
