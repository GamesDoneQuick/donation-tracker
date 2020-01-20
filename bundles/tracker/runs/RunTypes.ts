import { DateTime } from '../../public/util/TimeUtils';

export type Run = {
  id?: string;
  name: string;
  displayName: string;
  twitchName: string;
  canonicalUrl?: string;
  public: string;
  category?: string;
  description: string;
  console: string;
  releaseYear?: number;
  deprecatedRunners: string;
  commentators: string;
  startTime?: DateTime;
  endTime?: DateTime;
  runTime: string;
  setupTime: string;
  order?: number;
  coop: boolean;
  runners: string[]; // Runner[]
  techNotes?: string;
  giantbombId?: string;
};
