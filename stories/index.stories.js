import React from 'react';

import { storiesOf } from '@storybook/react';
import { action } from '@storybook/addon-actions';

import InterstitialEditor from '../bundles/admin/interstitials/Editor/Table';
import moment from 'moment-timezone';
import ErrorBoundary from '../bundles/public/errorBoundary';

storiesOf('Interstitials', module).add('with stuff', () => (
  <ErrorBoundary>
    <InterstitialEditor
      interstitials={[
        {
          pk: 1,
          model: 'tracker.interview',
          fields: {
            order: 1,
            suborder: 1,
            interviewers: 'feasel',
            interviewees: 'SpikeVegeta',
            subject: 'How Awesome We Are',
            producer: 'skavenger',
            camera_operator: 'Richard',
            social_media: true,
            clips: true,
            length: '5:00',
          },
        },
      ]}
      runs={[
        {
          pk: 1,
          model: 'tracker.speedrun',
          fields: {
            order: 1,
            name: 'Test Run',
            starttime: moment('2019-06-23T16:00:00Z'),
            endtime: moment('2019-06-23T16:30:00Z'),
            setup_time: moment.duration(5, 'minutes'),
            run_time: moment.duration(25, 'minutes'),
          },
        },
        {
          pk: 2,
          model: 'tracker.speedrun',
          fields: {
            order: null,
            name: 'Unordered Run',
            starttime: null,
            endtime: null,
            setup_time: moment.duration(5, 'minutes'),
            run_time: moment.duration(25, 'minutes'),
          },
        },
      ]}
      saveError={null}
      saveItem={action('saveItem')}
      moveInterstitial={action('moveInterstitial')}
    />
  </ErrorBoundary>
));
