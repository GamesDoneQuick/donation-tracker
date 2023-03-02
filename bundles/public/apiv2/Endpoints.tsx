/**
 * This is for API v2 only. V1 usages in admin go through `@public/api` and the reducers there.
 */

const Endpoints = {
  DONATIONS_UNPROCESSED: `donations/unprocessed/`,
  DONATIONS_FLAGGED: `donations/flagged/`,
  DONATIONS_COUNTS: `donations/counts/`,
  DONATIONS_UNPROCESS: (donationId: string) => `donations/${donationId}/unprocess/`,
  DONATIONS_APPROVE_COMMENT: (donationId: string) => `donations/${donationId}/approve_comment/`,
  DONATIONS_DENY_COMMENT: (donationId: string) => `donations/${donationId}/deny_comment/`,
  DONATIONS_FLAG: (donationId: string) => `donations/${donationId}/flag/`,
  DONATIONS_SEND_TO_READER: (donationId: string) => `donations/${donationId}/send_to_reader/`,
  DONATIONS_PIN: (donationId: string) => `donations/${donationId}/pin/`,
  DONATIONS_UNPIN: (donationId: string) => `donations/${donationId}/unpin/`,
  EVENTS: `events/`,
  EVENT: (eventId: string) => `events/${eventId}/`,
};

export default Endpoints;
