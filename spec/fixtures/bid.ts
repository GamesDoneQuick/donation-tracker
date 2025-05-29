import {
  asBidChain,
  asBidChild,
  BidChain,
  BidChild,
  findChainInTree,
  FlatBid,
  PaginationInfo,
  TreeBid,
} from '@public/apiv2/APITypes';
import { DonationBid, VALID_PARENT_STATES } from '@public/apiv2/Models';

import { Incentive } from '@tracker/event_details/EventDetailsTypes';

// TODO: amount and count should be computed fields, similar to event totals

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

function goalForStep(i: number) {
  console.assert(i < 19);
  return Math.max(5, 100 - i * 5);
}

function flatToTree(bids: FlatBid[]): TreeBid[] {
  const tree: TreeBid[] = [];
  bids.forEach(b => {
    if (b.parent == null) {
      const { level, parent, ...rest } = b;
      tree.push(rest);
    }
  });
  bids.forEach(b => {
    const bcn = asBidChain(b);
    if (bcn) {
      const t = findChainInTree(tree, b.parent!);
      if (t) {
        t.chain_steps ??= [];
        t.chain_steps.push(bcn);
      }
    }
    const bcd = asBidChild(b);
    if (bcd) {
      const t = tree.find(t => t.id === b.parent);
      if (t) {
        t.options ??= [];
        t.options.push(bcd);
      }
    }
  });
  return tree;
}

export function getFixtureMixedBidsFlat(
  challengeOverrides?: Omit<Partial<FlatBid>, 'level' | 'parent' | 'id' | 'istarget'>,
  parentOverrides?: Omit<Partial<FlatBid>, 'level' | 'parent' | 'id' | 'istarget'>,
  acceptedChildOverrides?: Omit<Partial<FlatBid>, 'level' | 'parent' | 'state' | 'id' | 'event' | 'istarget'>,
  pendingChildOverrides?: Omit<Partial<FlatBid>, 'level' | 'parent' | 'state' | 'id' | 'event' | 'istarget'>,
  extraChildrenOverrides?: Array<Omit<Partial<FlatBid>, 'level' | 'parent' | 'id' | 'event' | 'istarget'>>,
  chainOverrides?: Array<
    Omit<Partial<FlatBid>, 'level' | 'parent' | 'id' | 'chain' | 'chain_goal' | 'chain_remaining' | 'istarget'>
  >,
): PaginationInfo<FlatBid> {
  const challengeState = challengeOverrides?.state ?? 'OPENED';
  console.assert(VALID_PARENT_STATES.includes(challengeState));
  const parentState = parentOverrides?.state ?? 'OPENED';
  console.assert(VALID_PARENT_STATES.includes(parentState));
  const parentEvent = parentOverrides?.event;
  const parentRun = parentOverrides?.speedrun ?? null;
  const acceptedTotal = acceptedChildOverrides?.total ?? 25;
  const acceptedCount = acceptedChildOverrides?.count ?? 2;
  // pending/denied/hidden
  const pendingTotal = pendingChildOverrides?.total ?? 20;
  const pendingCount = pendingChildOverrides?.count ?? 1;
  const countedOverrides = (extraChildrenOverrides ?? []).filter(o =>
    VALID_PARENT_STATES.includes(o.state ?? parentState),
  );
  const parentTotal = acceptedTotal + countedOverrides.reduce((t, o) => t + (o.total ?? 0), 0);
  const parentCount = acceptedCount + countedOverrides.reduce((t, o) => t + (o.count ?? 0), 0);
  const chainFirstId = 125 + (extraChildrenOverrides?.length ?? 0);
  chainOverrides = chainOverrides ?? [];
  while (chainOverrides.length < 3) {
    chainOverrides.push({});
  }
  const chainState = chainOverrides[0].state ?? 'OPENED';
  console.assert(VALID_PARENT_STATES.includes(chainState));
  const chainTotal = chainOverrides[0].total ?? 0;
  const chainEvent = chainOverrides[0].event;
  const chainRun = chainOverrides[0].speedrun ?? null;

  return {
    count: 4 + (extraChildrenOverrides?.length ?? 0) + Math.max(3, chainOverrides?.length ?? 0),
    previous: null,
    next: null,
    results: [
      {
        id: 121,
        level: 0,
        parent: null,
        type: 'bid',
        bid_type: 'challenge',
        name: 'Goal',
        speedrun: null,
        state: challengeState,
        description: 'Extra Secret Level',
        shortdescription: '',
        estimate: '0:10:00',
        close_at: 'end of run',
        post_run: true,
        goal: 1000,
        chain: false,
        total: 75,
        count: 3,
        istarget: true,
        revealedtime: null,
        allowuseroptions: false,
        ...challengeOverrides,
      },
      {
        id: 122,
        level: 0,
        parent: null,
        type: 'bid',
        bid_type: 'choice',
        name: 'Naming Incentive',
        speedrun: parentRun,
        state: parentState,
        description: 'Name the Character',
        shortdescription: '',
        estimate: null,
        close_at: null,
        post_run: false,
        goal: null,
        chain: false,
        total: parentTotal,
        count: parentCount,
        istarget: false,
        revealedtime: null,
        allowuseroptions: true,
        option_max_length: 12,
        ...(parentEvent ? { event: parentEvent } : {}),
        ...parentOverrides,
      },
      {
        id: 123,
        type: 'bid',
        level: 1,
        goal: null,
        speedrun: parentRun,
        close_at: null,
        post_run: false,
        chain: false,
        parent: 122,
        bid_type: 'option',
        name: 'Approved',
        description: '',
        shortdescription: '',
        estimate: null,
        istarget: true,
        revealedtime: null,
        state: parentState,
        total: acceptedTotal,
        count: acceptedCount,
        ...(parentEvent ? { event: parentEvent } : {}),
        ...acceptedChildOverrides,
      },
      {
        id: 124,
        type: 'bid',
        level: 1,
        goal: null,
        speedrun: null,
        close_at: null,
        post_run: false,
        chain: false,
        parent: 122,
        bid_type: 'option',
        name: 'Unapproved',
        description: '',
        shortdescription: '',
        estimate: null,
        istarget: true,
        revealedtime: null,
        state: 'PENDING',
        total: pendingTotal,
        count: pendingCount,
        ...(parentEvent ? { event: parentEvent } : {}),
        ...pendingChildOverrides,
      },
      ...(extraChildrenOverrides ?? []).map(
        (overrides, i): FlatBid => ({
          id: 125 + i,
          type: 'bid',
          level: 1,
          goal: null,
          speedrun: parentRun,
          close_at: null,
          post_run: false,
          chain: false,
          parent: 122,
          bid_type: 'option',
          name: `Extra Option ${i}`,
          description: '',
          shortdescription: '',
          estimate: null,
          istarget: true,
          revealedtime: null,
          state: parentState,
          total: 0,
          count: 0,
          ...(parentEvent ? { event: parentEvent } : {}),
          ...overrides,
        }),
      ),
      ...chainOverrides.map((overrides, i, chain): FlatBid => {
        const goal = overrides.goal ?? goalForStep(i);
        return {
          id: chainFirstId + i,
          type: 'bid',
          level: i,
          goal,
          close_at: null,
          post_run: false,
          chain: true,
          parent: i === 0 ? null : chainFirstId + i - 1,
          bid_type: 'challenge',
          name: `Chain Step ${i + 1}`,
          description: '',
          shortdescription: '',
          estimate: null,
          istarget: i === 0,
          revealedtime: null,
          count: 0,
          chain_goal: chain.slice(0, i + 1).reduce((t, c) => t + (c.goal ?? goalForStep(i - 1)), 0),
          chain_remaining: chain.slice(i + 1).reduce((t, c, n) => t + (c.goal ?? goalForStep(i + n + 1)), 0),
          ...overrides,
          ...(chainEvent ? { event: chainEvent } : {}),
          total: Math.max(0, chainTotal - chain.slice(0, i).reduce((t, c, n) => t + (c.goal ?? goalForStep(i + n)), 0)),
          state: chainState,
          speedrun: chainRun,
        };
      }),
    ],
  };
}

export function getFixtureMixedBidsTree(
  challengeOverrides?: Partial<Omit<TreeBid, 'id' | 'options_max_length' | 'options'>>,
  parentOverrides?: Partial<Omit<TreeBid, 'id' | 'options'>>,
  acceptedChildOverrides?: Partial<Omit<BidChild, 'state'>>,
  pendingChildOverrides?: Partial<Omit<BidChild, 'state'>>,
  extraChildrenOverrides?: BidChild[],
  chainOverrides?: Omit<
    Partial<TreeBid>,
    'id' | 'chain' | 'chain_goal' | 'chain_remaining' | 'chain_steps' | 'istarget'
  >,
  chainStepOverrides?: Array<Omit<Partial<BidChain>, 'id' | 'chain_goal' | 'chain_remaining'>>,
): PaginationInfo<TreeBid> {
  const flatChainOverrides: Array<
    Omit<Partial<FlatBid>, 'level' | 'parent' | 'id' | 'chain' | 'chain_goal' | 'chain_remaining' | 'istarget'>
  > = [];
  if (chainOverrides) {
    flatChainOverrides.push(chainOverrides);
  }
  flatChainOverrides.push(...(chainStepOverrides ?? []));
  const flat = getFixtureMixedBidsFlat(
    challengeOverrides,
    parentOverrides,
    acceptedChildOverrides,
    pendingChildOverrides,
    extraChildrenOverrides,
    flatChainOverrides,
  );

  const tree = flatToTree(flat.results);

  return {
    count: flat.count,
    previous: null,
    next: null,
    results: tree,
  };
}

export function getFixtureDonationBid(overrides?: Partial<DonationBid>): DonationBid {
  return {
    id: 1,
    type: 'donationbid',
    donation: 501,
    bid: 701,
    bid_name: 'Default Bid',
    bid_state: 'OPENED',
    bid_count: 1,
    bid_total: 25,
    amount: 25,
    ...overrides,
  };
}
