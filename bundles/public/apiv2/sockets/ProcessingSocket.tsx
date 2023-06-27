import SturdyWebsocket from 'sturdy-websocket';

import { Donation } from '../APITypes';

export type ProcessingSocketEventType = 'connection_changed' | 'processing_action' | 'donation_received';

export type ProcessingActionType =
  | 'unprocessed'
  | 'approved'
  | 'denied'
  | 'flagged'
  | 'sent_to_reader'
  | 'pinned'
  | 'unpinned';

interface ProcessingActionEvent {
  type: 'processing_action';
  action: ProcessingActionType;
  actor_name: string;
  actor_id: number;
  donation: Donation;
}

interface DonationReceivedEvent {
  type: 'donation_received';
  donation: Donation;
  event_total: number;
  donation_count: number;
  posted_at: string;
}

interface ConnectionChangedEvent {
  type: 'connection_changed';
  isConnected: boolean;
}

export type ProcessingEvent = ProcessingActionEvent | DonationReceivedEvent | ConnectionChangedEvent;

type ProcessingEventMap = {
  processing_action: ProcessingActionEvent;
  donation_received: DonationReceivedEvent;
  connection_changed: ConnectionChangedEvent;
};

type ProcessingEventHandler = (event: ProcessingEvent) => unknown;

export class ProcessingSocketImpl {
  subscriptions: Map<ProcessingSocketEventType, Set<ProcessingEventHandler>>;
  isConnected: boolean;
  socket: SturdyWebsocket;

  constructor(url: string) {
    this.subscriptions = new Map();
    this.isConnected = false;

    this.socket = new SturdyWebsocket(url);
    this.socket.onmessage = this.handleMessage;
    this.socket.onopen = () => this.handleConnectionChange(true);
    this.socket.onclose = () => this.handleConnectionChange(false);
    this.socket.onreopen = () => this.handleConnectionChange(true);
    this.socket.ondown = () => this.handleConnectionChange(false);
  }

  on<T extends ProcessingSocketEventType>(eventType: T, handler: (event: ProcessingEventMap[T]) => unknown) {
    if (!this.subscriptions.has(eventType)) {
      this.subscriptions.set(eventType, new Set());
    }

    this.subscriptions.get(eventType)?.add(handler as ProcessingEventHandler);

    return () => {
      this.subscriptions.get(eventType)?.delete(handler as ProcessingEventHandler);
    };
  }

  handleConnectionChange(connected: boolean) {
    this.isConnected = connected;
    this._emit('connection_changed', { type: 'connection_changed', isConnected: connected });
  }

  handleMessage = (event: MessageEvent) => {
    const data = JSON.parse(event.data) as ProcessingEvent;
    this._emit(data.type, data);
  };

  private _emit(eventType: ProcessingSocketEventType, data: ProcessingEvent) {
    const subscribers = this.subscriptions.get(eventType) || new Set();
    for (const subscriber of subscribers) {
      subscriber(data);
    }
  }
}
