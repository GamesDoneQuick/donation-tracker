import { PaginationInfo, TreeBid } from '@gamesdonequick/donation-tracker-api-types';

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
