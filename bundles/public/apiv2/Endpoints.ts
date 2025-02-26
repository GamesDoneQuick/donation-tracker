import { DonationState } from '@public/apiv2/reducers/trackerApi';

export type BidFeed = 'pending' | 'all' | 'current' | 'open' | 'closed' | 'public';

function prependEvent(url: string, eventId?: number) {
  return `${eventId != null ? `events/${eventId}/` : ''}${url}`;
}

const Endpoints = {
  DONATIONS: ({ eventId, state }: { eventId?: number; state?: DonationState } = {}) =>
    prependEvent(`donations/${state ? `${state}/` : ''}`, eventId),
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
  BIDS: ({ eventId, feed, tree }: { eventId?: number; feed?: BidFeed; tree?: boolean } = {}) =>
    prependEvent(`bids/${feed && feed !== 'public' ? `feed_${feed}/` : ''}${tree ? 'tree/' : ''}`, eventId),
  BID: (id: number, { eventId }: { eventId?: number }) => prependEvent(`bids/${id}/`, eventId),
  APPROVE_BID: (id: number) => `bids/${id}/approve/`,
  DENY_BID: (id: number) => `bids/${id}/deny/`,
  RUNS: (eventId?: number) => prependEvent('runs/', eventId),
  RUN: (id: number, { eventId }: { eventId?: number } = {}) => prependEvent(`runs/${id}/`, eventId),
  INTERVIEWS: (eventId?: number) => prependEvent('interviews/', eventId),
  INTERVIEW: (id: number, { eventId }: { eventId?: number } = {}) => prependEvent(`interviews/${id}`, eventId),
  ADS: (eventId?: number) => prependEvent('ads/', eventId),
  AD: (id: number, { eventId }: { eventId?: number } = {}) => prependEvent(`ad/${id}`, eventId),
  MOVE_RUN: (id: number) => `runs/${id}/move/`,
  PRIZES: (eventId?: number) => prependEvent('prizes/', eventId),
  EVENTS: `events/`,
  EVENT: (id: number) => `events/${id}/`,
  MILESTONES: (eventId?: number) => prependEvent('milestones/', eventId),
  ME: `me/`,
  DONATION_GROUPS: 'donation_groups/',
  DONATION_GROUP: (slug: string) => `donation_groups/${slug}/`,
};

export default Endpoints;
