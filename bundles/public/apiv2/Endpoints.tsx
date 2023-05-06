/**
 * This is for API v2 only. V1 usages in admin go through `@public/api` and the reducers there.
 */

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
  BIDS: (eventId?: number, feed?: string, tree?: boolean) =>
    `${eventId == null ? '' : `events/${eventId}/`}bids/${feed ? `feed_${feed}/` : ''}${tree ? 'tree/' : ''}`,
  BID: (bidId: number) => `bids/${bidId}/`,
  EVENTS: `events/`,
  EVENT: (eventId: string) => `events/${eventId}/`,
  ME: `me/`,
};

export default Endpoints;
