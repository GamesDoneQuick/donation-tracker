import * as donations from './routes/donations';
import * as events from './routes/events';
import * as me from './routes/me';

const client = {
  ...donations,
  ...events,
  ...me,
};

export default client;
