import * as donations from './routes/donations';
import * as events from './routes/events';
import * as me from './routes/me';
import { sockets } from './sockets';

const client = {
  ...donations,
  ...events,
  ...me,
  sockets,
};

export default client;
