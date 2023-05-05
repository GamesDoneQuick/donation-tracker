export type ModelType = 'bid';

export interface Model {
  readonly type: string;
  readonly id: number;
}

export type BidState = 'PENDING' | 'DENIED' | 'HIDDEN' | 'OPENED' | 'CLOSED';

interface BidBase extends Model {
  readonly parent?: number;
  name: string;
  state: BidState;
  description: string;
  shortdescription: string;
  goal?: number;
  istarget: boolean;
  readonly revealedtime?: Date;
  biddependency?: number;
  readonly total: number;
  readonly count: number;
  pinned: boolean;
}

export interface ChallengeBid extends BidBase {
  event: number;
  speedrun?: number;
  readonly parent: undefined;
  goal: number;
  repeat?: number;
  istarget: true;
}

export interface BidTrunk extends BidBase {
  event: number;
  speedrun?: number;
  readonly parent: undefined;
  chain: false;
  istarget: false;
  goal: number;
  allowuseroptions: boolean;
  option_max_length?: number;
  options: number[];
}

export interface BidBranch extends BidBase {
  readonly parent: number;
  chain: false;
  istarget: false;
  options: number[];
}

type BidParent = BidTrunk | BidBranch;

export interface BidLeaf extends BidBase {
  readonly parent: number;
  chain: false;
  istarget: true;
}

export interface ChainedBid extends BidBase {
  chain: true;
  goal: number;
  readonly chain_threshold: number;
  readonly chain_remaining: number;
}

export interface ChainedBidStart extends ChainedBid {
  event: number;
  speedrun?: number;
  readonly parent: undefined;
  chain_steps: number[];
}

export interface ChainedBidStep extends ChainedBid {
  readonly parent: number;
}

export type Bid = BidTrunk | BidBranch | BidLeaf | ChallengeBid | ChainedBidStart | ChainedBidStep;

export function findParent(bids: Bid[], child: Bid) {
  return bids.find(parent => parent.id === child.parent) as BidParent;
}
