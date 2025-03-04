import { DateTime, Duration } from 'luxon';
import {
  Ad as APIAd,
  Donation as APIDonation,
  Donor,
  Event as APIEvent,
  Interstitial as APIInterstitial,
  Interview as APIInterview,
  Milestone as APIMilestone,
  ModelType,
  Prize as APIPrize,
  Run as APIRun,
  Talent,
} from '@gamesdonequick/donation-tracker-api-types';

type WithEvent<T extends { event?: unknown }> = Omit<T, 'event'> & { event: number };

export interface Event extends Omit<APIEvent, 'datetime'> {
  datetime: DateTime;
}

export interface Donation extends Omit<WithEvent<APIDonation>, 'timereceived'> {
  timereceived: DateTime;
}

export interface Run
  extends Omit<WithEvent<APIRun>, 'starttime' | 'endtime' | 'run_time' | 'setup_time' | 'anchor_time'> {
  starttime: null | DateTime;
  endtime: null | DateTime;
  run_time: Duration;
  setup_time: Duration;
  anchor_time: DateTime | null;
}

export interface UnorderedRun extends Run {
  order: null;
  starttime: null;
  endtime: null;
}

export interface OrderedRun extends Run {
  order: number;
  starttime: DateTime;
  endtime: DateTime;
}

export interface AnchoredRun extends OrderedRun {
  anchor_time: DateTime;
}

export interface Milestone extends WithEvent<APIMilestone> {
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

type Interstitial<I extends APIInterstitial, T extends ModelType> = Omit<WithEvent<I>, 'length'> & {
  readonly type: T;
  length: luxon.Duration;
};

export type Interview = Interstitial<APIInterview, 'interview'>;

export type Ad = Interstitial<APIAd, 'ad'>;

export interface Prize
  extends Omit<WithEvent<APIPrize>, 'starttime' | 'endtime' | 'start_draw_time' | 'end_draw_time'> {
  starttime: null | luxon.DateTime;
  endtime: null | luxon.DateTime;
  start_draw_time: null | luxon.DateTime;
  end_draw_time: null | luxon.DateTime;
}

export interface TimedPrize extends Prize {
  start_draw_time: luxon.DateTime;
  end_draw_time: luxon.DateTime;
}

export type Model = Event | Ad | Interview | Run | Milestone | Prize | Talent | Donor;
