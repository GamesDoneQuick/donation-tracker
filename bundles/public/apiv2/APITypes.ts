import { Permission } from '@common/Permissions';
import {
  Ad,
  BidBase,
  BidState,
  Country,
  CountryRegion,
  Donation,
  DonationBid,
  DonationDomain,
  Donor,
  Event,
  Interview,
  Milestone,
  Prize,
  PrizeState,
  Run,
  Talent,
} from '@public/apiv2/Models';
import { MaybeArray } from '@public/util/Types';

export type Me = {
  username: string;
  superuser: boolean;
  staff: boolean;
  permissions: Permission[];
};

type SingleKey = number | string | [string];

export type EventAPIId = SingleKey;
export type TalentAPIId = SingleKey;
export type RunAPId = number | [string, string, [string]];
export type DonorVisibility = 'FULL' | 'FIRST' | 'ALIAS' | 'ANON';

export interface BidChain
  extends Omit<BidBase, 'event' | 'speedrun' | 'parent' | 'chain' | 'repeat' | 'allowuseroptions'> {
  readonly bid_type: 'challenge';
  goal: number;
  chain_goal: number;
  chain_remaining: number;
}

export interface BidChild
  extends Omit<
    BidBase,
    'event' | 'speedrun' | 'parent' | 'chain' | 'allowuseroptions' | 'close_at' | 'post_run' | 'repeat' | 'goal'
  > {
  readonly bid_type: 'choice' | 'option';
  options?: BidChild[];
}

export interface FlatBid extends Omit<BidBase, 'event' | 'options' | 'repeat' | 'allowuseroptions'> {
  event?: number;
  repeat?: number | null;
  allowuseroptions?: boolean;
  level: number;
}

export interface TreeBid extends Omit<BidBase, 'event' | 'repeat' | 'allowuseroptions' | 'level' | 'parent'> {
  event?: number;
  allowuseroptions?: boolean;
  options?: BidChild[];
  chain_steps?: BidChain[];
}

/**
 * searches both the top level bids and the children for the specified bid
 */
export function findBidInTree(bids: TreeBid[], matcher: number | ((o: TreeBid | BidChild) => boolean)) {
  if (typeof matcher === 'number') {
    const id = matcher;
    matcher = (o: TreeBid | BidChild) => o.id === id;
  }
  return bids.find(matcher) ?? bids.find(b => b.options?.some(matcher))?.options?.find(matcher);
}

/**
 * same as findBidInTree but only searches for children
 */
export function findChildInTree(bids: TreeBid[], matcher: number | ((o: BidChild) => boolean)) {
  if (typeof matcher === 'number') {
    const id = matcher;
    matcher = (o: BidChild) => o.id === id;
  }
  return bids.find(b => b.options?.some(matcher))?.options?.find(matcher);
}

/**
 * searches for the parent containing the specified chain step
 */
export function findChainInTree(bids: TreeBid[], matcher: number | ((o: TreeBid | BidChain) => boolean)) {
  if (typeof matcher === 'number') {
    // will match any step in the chain
    const id = matcher;
    matcher = (o: TreeBid | BidChain) => o.id === id;
  }
  return bids.find(
    (b): b is TreeBid & { chain: true; chain_steps: BidChain[]; chain_goal: number; chain_remaining: number } =>
      b.chain && !!(matcher(b) || b.chain_steps?.some(matcher)),
  );
}

export function asBidChild(bid: FlatBid): BidChild | undefined {
  const { bid_type, level, parent, ...rest } = bid;
  // TODO: strip out the rest of the fields
  if ((bid_type === 'choice' || bid_type === 'option') && bid.parent != null) {
    return {
      bid_type,
      ...rest,
    };
  }
}

export function asBidChain(bid: FlatBid): BidChain | undefined {
  if (
    bid.bid_type === 'challenge' &&
    bid.parent != null &&
    bid.chain &&
    bid.goal != null &&
    bid.chain_goal != null &&
    bid.chain_remaining != null
  ) {
    // TODO: strip out the rest of the fields
    const { bid_type, level, parent, goal, chain_remaining, chain_goal, ...rest } = bid;
    return {
      bid_type: 'challenge',
      goal,
      chain_remaining,
      chain_goal,
      ...rest,
    };
  }
}

export interface BidGet {
  all?: string;
  now?: string;
}

export interface BidPost {
  event?: EventAPIId;
  name: string;
  speedrun?: RunAPId;
  parent?: number;
  goal?: number;
  state?: BidState;
}

export type BidPatch = Omit<Partial<BidPost>, 'event'>;

export interface APIEvent extends Omit<Event, 'datetime'> {
  datetime: string;
}

export interface EventGet {
  id?: MaybeArray<number>;
  short?: string;
  totals?: string;
}

export interface APIDonation extends Omit<Donation, 'event' | 'timereceived'> {
  event?: number;
  timereceived: string;
}

export interface DonationGet {
  id?: MaybeArray<number>;
  all?: '';
  all_bids?: '';
  time_gte?: string;
}

export interface APIRun
  extends Omit<Run, 'event' | 'starttime' | 'endtime' | 'run_time' | 'setup_time' | 'anchor_time'> {
  event?: APIEvent;
  starttime: null | string;
  endtime: null | string;
  run_time: string;
  setup_time: string;
  anchor_time: null | string;
}

export interface RunGet {
  tech_notes?: string;
  all?: string;
}

export interface RunPost {
  event?: EventAPIId;
  name: string;
  category: string;
  display_name?: string;
  twitch_name?: string;
  description?: string;
  coop?: boolean;
  onsite?: 'ONSITE' | 'ONLINE' | 'HYBRID';
  release_year?: number;
  console?: string;
  order?: number | 'last';
  runners: TalentAPIId[];
  hosts?: TalentAPIId[];
  commentators?: TalentAPIId[];
  run_time: string;
  setup_time: string;
  anchor_time?: string | null;
  tech_notes?: string;
  video_links?: Array<{
    link_type: string;
    url: string;
  }>;
  priority_tag?: null | string;
  tags?: string[];
}

export type RunPatch = Partial<RunPost>;

export interface APIMilestone extends Omit<Milestone, 'event'> {
  event?: APIEvent;
}

export interface MilestoneGet {
  all?: string;
}

export interface MilestonePost {
  event?: EventAPIId;
  name: string;
  amount: number;
  run?: RunAPId;
}

export type MilestonePatch = Partial<MilestonePost>;

export type APIInterstitial<T = object, F extends string | number | symbol = never> = Omit<
  T,
  'event' | 'length' | F
> & {
  event?: number | APIEvent;
  length: string;
};

export type APIInterview = APIInterstitial<Interview>;

interface InterstitialPost {
  event?: EventAPIId;
  anchor?: RunAPId;
  order?: number;
  suborder: number | 'last';
  length: string;
  tags?: string[];
}

export interface InterviewGet {
  all?: string;
}

export interface InterviewPost extends InterstitialPost {
  interviewers: TalentAPIId[];
  subjects?: TalentAPIId[];
  topic: string;
}

export type InterviewPatch = Partial<InterviewPost>;

export type APIAd = APIInterstitial<Ad>;

export interface AdPost extends InterstitialPost {
  filename: string;
  sponsor_name: string;
  ad_name: string;
  ad_type: 'VIDEO' | 'IMAGE';
  blurb?: string;
}

export type AdPatch = Partial<AdPost>;

export interface APIPrize extends Omit<Prize, 'event' | 'starttime' | 'endtime' | 'start_draw_time' | 'end_draw_time'> {
  event?: APIEvent;
  starttime: null | string;
  endtime: null | string;
  start_draw_time: null | string;
  end_draw_time: null | string;
}

export interface PrizeGet {
  time?: string;
  state?: MaybeArray<PrizeState>;
  name?: string;
  q?: string;
  run?: number;
}

export interface PrizePost {
  event?: EventAPIId;
  name: string;
  startrun?: number;
  endrun?: number;
  starttime?: string;
  endtime?: string;
  description?: string;
  shortdescription?: string;
  image?: string;
  altimage?: string;
  estimatedvalue?: number;
  minimumbid?: number;
  sumdonations?: boolean;
  provider?: string;
  creator?: string;
  creatorwebsite?: string;
  state?: PrizeState;
}

export type PrizePatch = Partial<PrizePost>;

export interface TalentGet {
  name?: string;
}

export interface TalentPost {
  name: string;
  stream?: string;
  twitter?: string;
  youtube?: string;
  pronouns?: string;
}

export type TalentPatch = Partial<TalentPost>;

export interface DonationCommentPatch {
  comment: string;
}

export interface DonorGet {
  totals?: string;
  /**
   * @deprecated use `totals` instead
   */
  include_totals?: string;
}

export type APIModel =
  | APIAd
  | APIDonation
  | APIEvent
  | APIInterstitial
  | APIInterview
  | APIMilestone
  | APIPrize
  | APIRun
  | FlatBid
  | TreeBid
  | Country
  | CountryRegion
  | DonationBid
  | Donor
  | Talent;

export interface PaginationInfo<T> {
  count: number;
  next: null | string;
  previous: null | string;
  results: T[];
}

// from `/ws/donations`

export interface SocketDonation {
  id: number;
  event: number;
  timereceived: string;
  comment: string;
  amount: number;
  donor__visibility: DonorVisibility;
  donor__visiblename: string;
  new_total: number;
  domain: DonationDomain;
  // unlike APIDonation, this is the bids from the attachments, not the attachments themselves
  bids: Array<{
    id: number;
    total: number;
    parent: number | null;
    name: string;
    goal: number | null;
    state: BidState;
    speedrun: number | null;
  }>;
}

// from `/ws/processing`

type DonationProcessingEventAction =
  | 'unprocessed'
  | 'approved'
  | 'denied'
  | 'flagged'
  | 'sent_to_reader'
  | 'pinned'
  | 'unpinned'
  | 'read'
  | 'ignored'
  | 'mod_comment_edited'
  | 'groups_changed';
type GroupProcessingEventAction = 'group_created' | 'group_deleted';

export type ProcessingEvent =
  | ({
      type: 'processing_action';
      actor_name: string;
      actor_id: number;
    } & (
      | {
          action: GroupProcessingEventAction;
          group: string;
        }
      | {
          action: DonationProcessingEventAction;
          donation: APIDonation;
        }
    ))
  | {
      type: 'donation_received';
      donation: APIDonation;
      event_total: number;
      donation_count: number;
      posted_at: string;
    };
