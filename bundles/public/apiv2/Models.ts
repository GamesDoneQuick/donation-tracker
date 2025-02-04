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

interface ModelBase {
  readonly type: ModelType;
  readonly id: number;
}

export interface Event extends ModelBase {
  readonly type: 'event';
  short: string;
  name: string;
  hashtag: string;
  datetime: luxon.DateTime;
  timezone: string;
  receivername: string;
  receiver_short: string;
  receiver_solicitation_text: string;
  receiver_logo: string;
  receiver_privacy_policy: string;
  paypalcurrency: string;
  use_one_step_screening: boolean;
  allow_donations: boolean;
  locked: boolean;
  // returned with '?totals'
  amount?: number;
  donation_count?: number;
}

export type DonationTransactionState = 'COMPLETED' | 'PENDING' | 'CANCELLED' | 'FLAGGED';
export type DonationDomain = 'PAYPAL' | 'LOCAL' | 'CHIPIN';
export type DonationReadState = 'PENDING' | 'READY' | 'IGNORED' | 'READ' | 'FLAGGED';
export type DonationCommentState = 'ABSENT' | 'PENDING' | 'DENIED' | 'APPROVED' | 'FLAGGED';

export interface Donation extends ModelBase {
  type: 'donation';
  donor?: number;
  donor_name: string;
  event: number;
  domain: DonationDomain;
  transactionstate: DonationTransactionState;
  readstate: DonationReadState;
  commentstate: DonationCommentState;
  amount: number;
  currency: string;
  timereceived: string;
  comment?: string;
  commentlanguage: string;
  pinned: boolean;
  bids: DonationBid[];
  modcomment?: string;
}

export type BidState = 'PENDING' | 'DENIED' | 'HIDDEN' | 'OPENED' | 'CLOSED';

export interface BidBase extends ModelBase {
  type: 'bid';
  readonly bid_type: 'challenge' | 'choice' | 'option';
  name: string;
  readonly event: number;
  readonly speedrun: null | number;
  readonly parent: null | number;
  state: BidState;
  description: string;
  shortdescription: string;
  estimate: null | string;
  close_at: null | string;
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

export interface Bid extends BidBase {
  level: number;
}

export function findParent(bids: Bid[], bid: Bid) {
  return bids.find(b => b.id === bid.parent);
}

interface RunBase extends ModelBase {
  readonly type: 'speedrun';
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
  starttime: null | luxon.DateTime;
  endtime: null | luxon.DateTime;
  order: number | null;
  tech_notes?: string;
  layout: string;
  run_time: luxon.Duration;
  setup_time: luxon.Duration;
  anchor_time: luxon.DateTime | null;
  video_links: object[];
  priority_tag: null | string;
  tags: string[];
}

export interface UnorderedRun extends RunBase {
  order: null;
  starttime: null;
  endtime: null;
}

export interface OrderedRun extends RunBase {
  order: number;
  starttime: luxon.DateTime;
  endtime: luxon.DateTime;
}

export type Run = OrderedRun | UnorderedRun;

export interface Milestone extends ModelBase {
  readonly type: 'milestone';
  event: number;
  name: string;
  run: null | number;
  start: number;
  amount: number;
  visible: boolean;
  description: string;
  short_description: string;
}

interface Interstitial extends ModelBase {
  anchor: null | number;
  event: number;
  order: number;
  suborder: number;
  tags: string[];
  length: luxon.Duration;
}

export interface Interview extends Interstitial {
  readonly type: 'interview';
  social_media: boolean;
  interviewers: number[];
  topic: string;
  subjects: number[];
  public: boolean;
  prerecorded: boolean;
  producer: string;
  camera_operator: string;
}

export interface Ad extends Interstitial {
  readonly type: 'ad';
  sponsor_name: string;
  ad_name: string;
  ad_type: string;
  filename: string;
  blurb: string;
}

export type PrizeState = 'ACCEPTED' | 'PENDING' | 'DENIED' | 'FLAGGED';

export interface Prize extends ModelBase {
  readonly type: 'prize';
  event: number;
  name: string;
  state: PrizeState;
  startrun: null | number;
  endrun: null | number;
  starttime: null | luxon.DateTime;
  endtime: null | luxon.DateTime;
  start_draw_time: null | luxon.DateTime;
  end_draw_time: null | luxon.DateTime;
  description: string;
  shortdescription: string;
  image: string;
  altimage: string;
  imagefile: null | string;
  estimatedvalue: null | number;
  minimumbid: number;
  sumdonations: boolean;
  provider: string;
  creator: null | string;
  creatorwebsite: null | string;
}

export interface Talent extends ModelBase {
  readonly type: 'talent';
  name: string;
  stream: string;
  twitter: string;
  youtube: string;
  platform: string;
  pronouns: string;
}

export interface Country extends Omit<ModelBase, 'id'> {
  readonly type: 'country';
  id?: undefined;
  name: string;
  alpha2: string;
  alpha3: string;
  numeric: null | string; // FIXME: is CN2 supposed to have a null numeric code?
}

export interface CountryRegion extends ModelBase {
  readonly type: 'countryregion';
  name: string;
  country: string; // alpha3
}

export interface Donor extends ModelBase {
  readonly type: 'donor';
  alias?: string;
  totals?: {
    event: null | number;
    total: number;
    count: number;
    avg: number;
    max: number;
  }[];
}

export interface DonationBid extends ModelBase {
  readonly type: 'donationbid';
  donation: number;
  bid: number;
  bid_name: string;
  bid_state: BidState;
  amount: number;
}

export type Model = Event | Interview | Bid | Run | Milestone | Prize | Talent | Donor;
