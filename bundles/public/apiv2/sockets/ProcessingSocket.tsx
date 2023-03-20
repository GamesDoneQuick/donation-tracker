import SturdyWebsocket from 'sturdy-websocket';

import { Donation } from '../APITypes';

export type ProcessingEventType =
  | 'bid_applied'
  | 'incentive_opened'
  | 'incentive_met'
  | 'donation_received'
  | 'donation_pending'
  | 'donation_completed'
  | 'donation_cancelled'
  | 'donation_comment_approved'
  | 'donation_comment_denied'
  | 'donation_comment_flagged'
  | 'donation_comment_sent_to_reader'
  | 'donation_comment_unprocessed'
  | 'donation_comment_automod_denied'
  | 'donation_comment_pinned'
  | 'donation_comment_unpinned'
  | 'request_served';

export interface ProcessingEvent {
  action: ProcessingEventType;
  actorName: string;
  actorId: number;
  donation: Donation;
}

type ProcessingEventHandler = (event: ProcessingEvent) => unknown;

export class ProcessingSocketImpl {
  subscriptions: Map<ProcessingEventType | '*', Set<ProcessingEventHandler>>;
  socket: SturdyWebsocket;

  constructor(url: string) {
    this.subscriptions = new Map();

    this.socket = new SturdyWebsocket(url);
    this.socket.onmessage = this.handleMessage;
  }

  on(eventType: ProcessingEventType | '*', handler: ProcessingEventHandler) {
    if (!this.subscriptions.has(eventType)) {
      this.subscriptions.set(eventType, new Set());
    }

    this.subscriptions.get(eventType)?.add(handler);

    return () => {
      this.subscriptions.get(eventType)?.delete(handler);
    };
  }

  handleMessage = (event: MessageEvent) => {
    const data = JSON.parse(event.data) as ProcessingEvent;
    const subscribers = this.subscriptions.get(data.action) || new Set();
    for (const subscriber of subscribers) {
      subscriber(data);
    }

    const allSubscribers = this.subscriptions.get('*') || new Set();
    for (const subscriber of allSubscribers) {
      subscriber(data);
    }
  };
}

export const ProcessingSocket = new ProcessingSocketImpl('ws://localhost:8000/tracker/ws/processing/');
