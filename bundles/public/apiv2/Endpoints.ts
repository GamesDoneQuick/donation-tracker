import { DonationState } from '@public/apiv2/reducers/trackerApi';

export type BidFeed = 'pending' | 'all' | 'current' | 'open' | 'closed' | 'public';
export type PrizeFeed = 'pending' | 'all' | 'current' | 'public' | 'to_draw';

function normalize(path: string) {
  return path.replace(/\/+/g, '/');
}

function prependEvent(path: string, eventId?: number | { eventId?: number }) {
  const actual = typeof eventId === 'number' ? eventId : eventId?.eventId;
  return normalize(`${actual != null ? `events/${actual}/` : ''}${path}`);
}

function appendFeed<T>(path: string, feed?: number | { feed?: T }) {
  const actual = typeof feed === 'number' ? null : feed?.feed;
  return normalize(`${path}${actual != null ? `/feed_${actual}/` : ''}`);
}

function appendState<T>(path: string, state?: number | { state?: T }) {
  const actual = typeof state === 'number' ? null : state?.state;
  return normalize(`${path}${actual != null ? `/${actual}/` : ''}`);
}

function appendTree(path: string, tree?: number | { tree?: boolean }) {
  const actual = typeof tree === 'number' ? false : tree?.tree;
  return normalize(`${path}${actual ? '/tree/' : ''}`);
}

const Endpoints = {
  DONATIONS: (params: number | { eventId?: number; state?: DonationState } = {}) =>
    appendState(prependEvent('donations', params), params),
  DONATIONS_UNPROCESS: (donationId: number) => `donations/${donationId}/unprocess/`,
  DONATIONS_APPROVE_COMMENT: (donationId: number) => `donations/${donationId}/approve_comment/`,
  DONATIONS_DENY_COMMENT: (donationId: number) => `donations/${donationId}/deny_comment/`,
  DONATIONS_FLAG: (donationId: number) => `donations/${donationId}/flag/`,
  DONATIONS_SEND_TO_READER: (donationId: number) => `donations/${donationId}/send_to_reader/`,
  DONATIONS_PIN: (donationId: number) => `donations/${donationId}/pin/`,
  DONATIONS_UNPIN: (donationId: number) => `donations/${donationId}/unpin/`,
  DONATIONS_READ: (donationId: number) => `donations/${donationId}/read/`,
  DONATIONS_IGNORE: (donationId: number) => `donations/${donationId}/ignore/`,
  DONATIONS_COMMENT: (donationId: number) => `donations/${donationId}/comment/`,
  DONATIONS_GROUPS: ({ donationId, group }: { donationId: number; group: string }) =>
    `donations/${donationId}/groups/${group}/`,
  BIDS: (params: number | { eventId?: number; feed?: BidFeed; tree?: boolean } = {}) =>
    appendTree(appendFeed(prependEvent('bids', params), params), params),
  BID: (id: number, { eventId }: { eventId?: number }) => prependEvent(`bids/${id}/`, eventId),
  APPROVE_BID: (id: number) => `bids/${id}/approve/`,
  DENY_BID: (id: number) => `bids/${id}/deny/`,
  RUNS: (eventId?: number) => prependEvent('runs/', eventId),
  RUN: (id: number, { eventId }: { eventId?: number } = {}) => prependEvent(`runs/${id}/`, eventId),
  MOVE_RUN: (id: number) => `runs/${id}/move/`,
  INTERVIEWS: (eventId?: number) => prependEvent('interviews/', eventId),
  INTERVIEW: (id: number, { eventId }: { eventId?: number } = {}) => prependEvent(`interviews/${id}/`, eventId),
  ADS: (eventId?: number) => prependEvent('ads/', eventId),
  AD: (id: number, { eventId }: { eventId?: number } = {}) => prependEvent(`ad/${id}/`, eventId),
  PRIZES: (params?: number | { eventId?: number; feed?: PrizeFeed }) =>
    appendFeed(prependEvent('prizes/', params), params),
  EVENTS: `events/`,
  EVENT: (id: number) => `events/${id}/`,
  MILESTONES: (eventId?: number) => prependEvent('milestones/', eventId),
  ME: `me/`,
  DONATION_GROUPS: 'donation_groups/',
  DONATION_GROUP: (slug: string) => `donation_groups/${slug}/`,
};

export default Endpoints;
