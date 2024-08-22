/**
 * This is for API v2 only. V1 usages in admin go through `@public/api` and the reducers there.
 */
import { BidFeed } from '@public/apiv2/actions/models';

function eventPath(id?: number) {
  return id == null ? '' : `events/${id}/`;
}

const Endpoints = {
  DONATIONS: `donations/`,
  DONATIONS_UNPROCESSED: `donations/unprocessed/`,
  DONATIONS_FLAGGED: `donations/flagged/`,
  DONATIONS_UNREAD: `donations/unread/`,
  DONATIONS_UNPROCESS: (donationId: string) => `donations/${donationId}/unprocess/`,
  DONATIONS_APPROVE_COMMENT: (donationId: string) => `donations/${donationId}/approve_comment/`,
  DONATIONS_DENY_COMMENT: (donationId: string) => `donations/${donationId}/deny_comment/`,
  DONATIONS_FLAG: (donationId: string) => `donations/${donationId}/flag/`,
  DONATIONS_SEND_TO_READER: (donationId: string) => `donations/${donationId}/send_to_reader/`,
  DONATIONS_PIN: (donationId: string) => `donations/${donationId}/pin/`,
  DONATIONS_UNPIN: (donationId: string) => `donations/${donationId}/unpin/`,
  DONATIONS_READ: (donationId: string) => `donations/${donationId}/read/`,
  DONATIONS_IGNORE: (donationId: string) => `donations/${donationId}/ignore/`,
  DONATIONS_COMMENT: (donationId: string) => `donations/${donationId}/comment/`,
  BIDS: (eventId?: number, feed?: BidFeed, tree?: boolean) =>
    `${eventPath(eventId)}bids/${feed && feed !== 'public' ? `feed_${feed}/` : ''}${
      tree ? 'tree/' : ''
    }`,
  BID: (bidId: number) => `bids/${bidId}/`,
  MILESTONES: (eventId?: number) => `${eventPath(eventId)}milestones/`,
  MILESTONE: (milestoneId: number) => `milestones/${milestoneId}/`,
  EVENTS: `events/`,
  EVENT: (eventId: string) => `events/${eventId}/`,
  RUNS: (eventId?: number) => `${eventPath(eventId)}runs/`,
  RUN: (runId: number) => `runs/${runId}/`,
  ME: `me/`,
};

export default Endpoints;
