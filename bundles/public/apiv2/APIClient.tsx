import * as donations from './routes/donations';
import * as events from './routes/events';
import * as me from './routes/me';
import * as processActions from './routes/process_actions';

const client = {
  ...donations,
  ...events,
  ...me,
  ...processActions,
};

export default client;
