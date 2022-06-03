import * as donations from './routes/donations';
import * as events from './routes/events';

const client = {
  ...donations,
  ...events,
};

export default client;
