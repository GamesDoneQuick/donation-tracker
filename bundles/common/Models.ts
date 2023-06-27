import moment from 'moment-timezone';

export interface ModelFields {
  [key: string]: any;
}

export interface Model {
  pk: number;
  model: string;
  canReorder: boolean;
  fields: ModelFields;
}

export interface OrderedFields extends ModelFields {
  order: number | null;
}

export interface SuborderedFields extends OrderedFields {
  order: number;
  suborder: number;
}

export interface Ordered extends Model {
  fields: OrderedFields;
}

export interface Subordered extends Ordered {
  fields: SuborderedFields;
}

export interface InterstitialFields extends SuborderedFields {
  length: string;
}

export interface Interstitial extends Model {
  fields: InterstitialFields;
}

export interface InterviewFields extends InterstitialFields {
  interviewers: string;
  subjects: string;
  topic: string;
  producer: string;
  camera_operator: string;
  social_media: boolean;
  clips: boolean;
  length: string;
}

export interface Interview extends Interstitial {
  model: 'tracker.interview';
  fields: InterviewFields;
}
enum AdType {
  image,
  video,
}

export interface AdFields extends InterstitialFields {
  sponsor_name: string;
  ad_name: string;
  ad_type: AdType;
  filename: string;
}

export interface Ad extends Interstitial {
  model: 'tracker.ad';
  fields: AdFields;
}

export interface RunFields extends ModelFields {
  display_name: string;
  starttime: moment.MomentZone | null;
  endtime: moment.MomentZone | null;
  setup_time: moment.Duration;
  run_time: moment.Duration;
  order: number;
}

export interface Run extends Model {
  model: 'tracker.speedrun';
  fields: RunFields;
}
