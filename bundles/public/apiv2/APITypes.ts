import { Permission } from './Permissions';

type MaybeArray<T> = T | T[];

export type ModelType =
  | 'ad'
  | 'bid'
  | 'country'
  | 'countryregion'
  | 'donation'
  | 'donationbid'
  | 'donor'
  | 'event'
  | 'interview'
  | 'milestone'
  | 'prize'
  | 'run'
  | 'speedrun'
  | 'talent';

interface ModelBase<T extends ModelType> {
  readonly type: T;
  readonly id: number;
}

export type Me = {
  username: string;
  superuser: boolean;
  staff: boolean;
  permissions: Permission[];
};

type SingleKey = number | string | [string];
type NestedModel<T extends Model> = number | T;
type Slug = string; // lowercase alphanumerics, dash, underscore (uppercase are converted before saving)
type URL = string;
type Duration = string; // e.g. '1:15:00' for an hour and 15 minutes
type ISOTimestamp = string;

export type EventAPIId = SingleKey;
export type TalentAPIId = SingleKey;
export type RunAPIId = number | [string, string, [string]];

export interface Event extends ModelBase<'event'> {
  short: Slug;
  name: string;
  hashtag: string;
  datetime: ISOTimestamp;
  timezone: string;
  receivername: string;
  receiver_short: string;
  receiver_solicitation_text: string;
  receiver_logo: URL;
  receiver_privacy_policy: URL;
  paypalcurrency: string;
  use_one_step_screening: boolean;
  allow_donations: boolean;
  locked: boolean;
  // returned with '?totals'
  amount?: number;
  donation_count?: number;
}

export interface EventGet {
  totals?: '';
}

export type BidState = 'PENDING' | 'DENIED' | 'HIDDEN' | 'OPENED' | 'CLOSED';

interface BidBase extends ModelBase<'bid'> {
  readonly bid_type: 'challenge' | 'choice' | 'option';
  name: string;
  readonly event: number;
  readonly speedrun: null | number;
  readonly parent: null | number;
  state: BidState;
  description: string;
  shortdescription: string;
  estimate: null | string;
  close_at: null | ISOTimestamp;
  post_run: boolean;
  goal: null | number;
  chain: boolean;
  chain_goal?: number;
  chain_remaining?: number;
  readonly total: number;
  readonly count: number;
  repeat: null | number;
  accepted_number?: number;
  istarget: boolean;
  allowuseroptions: boolean;
  option_max_length?: null | number;
  readonly revealedtime: null | string;
}

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

export interface TreeBid extends Omit<BidBase, 'event' | 'repeat' | 'allowuseroptions' | 'level' | 'parent'> {
  event?: number;
  allowuseroptions?: boolean;
  options?: BidChild[];
  chain_steps?: BidChain[];
}

export interface BidGet {
  all?: '';
  now?: ISOTimestamp;
}

export interface BidPost {
  event?: EventAPIId;
  name: string;
  speedrun?: RunAPIId;
  parent?: number;
  goal?: number;
  state?: BidState;
}

export type BidPatch = Omit<Partial<BidPost>, 'event'>;

export type DonationTransactionState = 'COMPLETED' | 'PENDING' | 'CANCELLED' | 'FLAGGED';
export type DonationDomain = 'PAYPAL' | 'LOCAL' | 'CHIPIN';
export type DonationReadState = 'PENDING' | 'READY' | 'IGNORED' | 'READ' | 'FLAGGED';
export type DonationCommentState = 'ABSENT' | 'PENDING' | 'DENIED' | 'APPROVED' | 'FLAGGED';

export interface Donation extends ModelBase<'donation'> {
  donor?: number;
  donor_name: string;
  event?: NestedModel<Event>;
  domain: DonationDomain;
  transactionstate: DonationTransactionState;
  readstate: DonationReadState;
  commentstate: DonationCommentState;
  amount: number;
  currency: string;
  timereceived: ISOTimestamp;
  comment?: string;
  commentlanguage: string;
  pinned: boolean;
  bids: DonationBid[];
  modcomment?: string;
}

export interface DonationGet {
  all?: '';
  all_bids?: '';
  time_gte?: ISOTimestamp;
}

export interface VideoLink {
  link_type: Slug;
  url: URL;
}

export interface Run extends ModelBase<'speedrun'> {
  event?: NestedModel<Event>;
  name: string;
  display_name: string;
  twitch_name: string;
  description: string;
  category: string;
  coop: boolean;
  onsite: 'ONSITE' | 'ONLINE' | 'HYBRID';
  console: string;
  release_year: number | null;
  runners: Talent[];
  hosts: Talent[];
  commentators: Talent[];
  order: number | null;
  tech_notes?: string;
  layout: string;
  video_links: VideoLink[];
  priority_tag: null | Slug;
  tags: Slug[];

  starttime: null | ISOTimestamp;
  endtime: null | ISOTimestamp;
  run_time: Duration;
  setup_time: Duration;
  anchor_time: null | ISOTimestamp;
}

export interface RunGet {
  tech_notes?: '';
  all?: '';
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
  run_time: Duration;
  setup_time: Duration;
  anchor_time?: ISOTimestamp | null;
  tech_notes?: string;
  video_links?: VideoLink[];
  priority_tag?: null | Slug;
  tags?: Slug[];
}

export type RunPatch = Partial<RunPost>;

export interface Milestone extends ModelBase<'milestone'> {
  event?: NestedModel<Event>;
  name: string;
  run: null | number;
  start: number;
  amount: number;
  visible: boolean;
  description: string;
  short_description: string;
}

export interface MilestoneGet {
  all?: '';
}

export interface MilestonePost {
  event?: EventAPIId;
  name: string;
  amount: number;
  run?: RunAPIId;
}

export type MilestonePatch = Partial<MilestonePost>;

export interface Interstitial extends ModelBase<'ad' | 'interview'> {
  event?: NestedModel<Event>;
  anchor: null | number;
  order: number;
  suborder: number;
  tags: Slug[];
  length: Duration;
}

export interface Interview extends Interstitial {
  readonly type: 'interview';
  social_media: boolean;
  topic: string;
  interviewers: Talent[];
  subjects: Talent[];
  public: boolean;
  prerecorded: boolean;
  producer: string;
  camera_operator: string;
}

type InterstitialPost = {
  suborder: number | 'last';
  length: Duration;
  tags?: Slug[];
} & (
  | {
      event: EventAPIId;
    }
  | {
      anchor: RunAPIId;
    }
  | {
      order: number;
    }
);

export interface InterviewGet {
  all?: '';
}

export type InterviewPost = InterstitialPost & {
  interviewers: TalentAPIId[];
  subjects?: TalentAPIId[];
  topic: string;
};

export type InterviewPatch = Partial<InterviewPost>;

export interface Ad extends Interstitial {
  readonly type: 'ad';
  sponsor_name: string;
  ad_name: string;
  ad_type: string;
  filename: string;
  blurb: string;
}

export type AdPost = InterstitialPost & {
  filename: string;
  sponsor_name: string;
  ad_name: string;
  ad_type: 'VIDEO' | 'IMAGE';
  blurb?: string;
};

export type AdPatch = Partial<AdPost>;

export type PrizeState = 'ACCEPTED' | 'PENDING' | 'DENIED' | 'FLAGGED';

export interface Prize extends ModelBase<'prize'> {
  event?: NestedModel<Event>;
  name: string;
  state: PrizeState;
  startrun: null | number;
  endrun: null | number;
  starttime: null | ISOTimestamp;
  endtime: null | ISOTimestamp;
  readonly start_draw_time: null | ISOTimestamp;
  readonly end_draw_time: null | ISOTimestamp;
  description: string;
  shortdescription: string;
  image: URL;
  altimage: URL;
  imagefile: null | URL;
  estimatedvalue: null | number;
  minimumbid: number;
  sumdonations: boolean;
  provider: string;
  creator: null | string;
  creatorwebsite: null | URL;
}

export interface PrizeGet {
  time?: ISOTimestamp;
  state?: MaybeArray<PrizeState>;
  name?: string;
  q?: string;
  run?: number;
}

export interface PrizePost {
  event?: EventAPIId;
  name: string;
  startrun?: RunAPIId;
  endrun?: RunAPIId;
  starttime?: ISOTimestamp;
  endtime?: ISOTimestamp;
  description?: string;
  shortdescription?: string;
  image?: URL;
  altimage?: URL;
  estimatedvalue?: number;
  minimumbid?: number;
  sumdonations?: boolean;
  provider?: string;
  creator?: string;
  creatorwebsite?: URL;
  state?: PrizeState;
}

export type PrizePatch = Partial<PrizePost>;

export interface Talent extends ModelBase<'talent'> {
  name: string;
  stream: URL;
  twitter: string;
  youtube: string;
  platform: string;
  pronouns: string;
}

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
  include_totals?: '';
}

export type Model =
  | Ad
  | Donation
  | Event
  | Interview
  | Milestone
  | Prize
  | Run
  | FlatBid
  | TreeBid
  | Country
  | CountryRegion
  | DonationBid
  | Donor
  | Talent;

export interface PaginationInfo<T extends Model | string = Model> {
  count: number;
  next: null | string;
  previous: null | string;
  results: T[];
}

export interface DonationBid extends ModelBase<'donationbid'> {
  donation: number;
  bid: number;
  bid_name: string;
  bid_state: BidState;
  amount: number;
}

interface DonorTotals {
  event: null | number;
  total: number;
  count: number;
  avg: number;
  max: number;
}

export interface Donor extends ModelBase<'donor'> {
  alias?: string;
  totals?: DonorTotals[];
}

export interface Country extends Omit<ModelBase<'country'>, 'id'> {
  name: string;
  alpha2: string;
  alpha3: string;
  numeric: null | string; // FIXME: is CN2 supposed to have a null numeric code?
}

export interface CountryRegion extends ModelBase<'countryregion'> {
  name: string;
  country: string; // alpha3
}
