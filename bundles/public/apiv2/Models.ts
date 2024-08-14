import luxon from 'luxon';
import { Duration, Moment } from 'moment';

export type ModelType = 'bid' | 'run';

export interface Model {
  readonly type: string;
  readonly id: number;
}

export type BidState = 'PENDING' | 'DENIED' | 'HIDDEN' | 'OPENED' | 'CLOSED';

interface BidBase extends Model {
  readonly type: 'bid';
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
  chain: false;
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
  options: BidChild[];
}

export interface BidBranch extends BidBase {
  readonly speedrun: undefined;
  readonly parent: number;
  chain: false;
  istarget: false;
  options: BidChild[];
}

export interface BidLeaf extends BidBase {
  readonly speedrun: undefined;
  readonly parent: number;
  chain: false;
  istarget: true;
}

export type BidParent = BidTrunk | BidBranch;
export type BidChild = BidBranch | BidLeaf;

export interface ChainedBid extends BidBase {
  chain: true;
  goal: number;
  readonly chain_goal: number;
  readonly chain_remaining: number;
}

export interface ChainedBidStart extends ChainedBid {
  event: number;
  speedrun?: number;
  readonly parent: undefined;
  chain_steps: ChainedBidStep[];
}

export interface ChainedBidStep extends ChainedBid {
  readonly speedrun: undefined;
  readonly parent: number;
}

export type Bid = BidTrunk | BidBranch | BidLeaf | ChallengeBid | ChainedBidStart | ChainedBidStep;

export function findParent(bids: Bid[], child: Bid) {
  return bids.find(parent => parent.id === child.parent) as BidParent;
}

export interface Run extends Model {
  type: 'speedrun';
  name: string;
  event: number;
  display_name: string;
  twitch_name: string;
  description: string;
  category: string | null;
  coop: boolean;
  onsite: 'ONSITE' | 'ONLINE' | 'HYBRID';
  console: string;
  release_year: number | null;
  runners: object[];
  hosts: object[];
  commentators: object[];
  starttime: luxon.DateTime;
  endtime: luxon.DateTime;
  order: number | null;
  run_time: luxon.Duration;
  setup_time: luxon.Duration;
  anchor_time: luxon.DateTime | null;
  video_links: object[];
}
