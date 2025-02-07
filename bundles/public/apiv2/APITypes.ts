import { Permission } from '@common/Permissions';
import {
  Ad,
  BidBase,
  BidState,
  Country,
  CountryRegion,
  Donation,
  DonationBid,
  Donor,
  Event,
  Interview,
  Milestone,
  Prize,
  PrizeState,
  Run,
  Talent,
} from '@public/apiv2/Models';

type MaybeArray<T> = T | T[];

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

interface BidChain extends Omit<BidBase, 'event' | 'speedrun' | 'parent' | 'chain' | 'repeat' | 'allowuseroptions'> {
  readonly bid_type: 'challenge';
  chain_goal: number;
  chain_remaining: number;
}

interface BidChild
  extends Omit<
    BidBase,
    'event' | 'speedrun' | 'parent' | 'chain' | 'allowuseroptions' | 'close_at' | 'post_run' | 'repeat' | 'goal'
  > {
  readonly bid_type: 'option';
  options?: BidChild[];
}

export interface FlatBid extends Omit<BidBase, 'event' | 'options' | 'repeat' | 'allowuseroptions'> {
  event?: number;
  repeat?: number | null;
  allowuseroptions?: boolean;
  level: number;
}

export interface TreeBid extends Omit<BidBase, 'event' | 'repeat' | 'allowuseroptions' | 'level'> {
  event?: number;
  allowuseroptions?: boolean;
  options?: BidChild[];
  chain_steps?: BidChain[];
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
  totals?: string;
}

export interface APIDonation extends Omit<Donation, 'event'> {
  event?: number;
}

export interface DonationGet {
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
  anchor_time?: string;
  tech_notes?: string;
  video_links?: {
    link_type: string;
    url: string;
  }[];
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

export interface APIInterview extends Omit<Interview, 'event' | 'length' | 'interviewers' | 'subjects'> {
  event?: number | APIEvent;
  length: string;
  interviewers: Talent[];
  subjects: Talent[];
}

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

export interface APIAd extends Omit<Ad, 'event' | 'length'> {
  event?: number | APIEvent;
  length: string;
}

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
  include_totals?: string;
}

export type APIModel =
  | APIAd
  | APIDonation
  | APIEvent
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

export interface PaginationInfo<T extends APIModel = APIModel> {
  count: number;
  next: null | string;
  previous: null | string;
  results: T[];
}
