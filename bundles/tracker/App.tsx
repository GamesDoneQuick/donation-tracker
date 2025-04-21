import React from 'react';
import { useParams } from 'react-router';
import { BrowserRouter, Route, Routes } from 'react-router-dom';

import { useConstants } from '@common/Constants';
import { useTrackerInit } from '@public/apiv2/hooks';

import Donate from '@tracker/donation/components/Donate';
import PrizeDetail from '@tracker/prizes/components/PrizeDetail';
import Prizes from '@tracker/prizes/components/Prizes';

import { AnalyticsEvent, setAnalyticsURL, track } from './analytics/Analytics';
import NotFound from './router/components/NotFound';

function PrizeRoute() {
  const { prizeId } = useParams();
  return <PrizeDetail prizeId={+prizeId!} />;
}

function DonateRoute() {
  return <Donate />;
}

const App = () => {
  const { ANALYTICS_URL, SWEEPSTAKES_URL, ROOT_PATH } = useConstants();
  const [ready, setReady] = React.useState(false);

  useTrackerInit();

  React.useLayoutEffect(() => {
    setAnalyticsURL(ANALYTICS_URL);
    setReady(true);
  }, [ANALYTICS_URL]);

  React.useLayoutEffect(() => {
    track(AnalyticsEvent.TRACKER_APP_LOADED, {
      react_render_finished_ms: Math.floor(window.performance.now()),
    });
  }, []);

  return (
    <>
      {ready && (
        <BrowserRouter basename={ROOT_PATH}>
          <Routes>
            <Route path="events/:eventId/">
              {SWEEPSTAKES_URL && <Route path="prizes" element={<Prizes />} />}
              {SWEEPSTAKES_URL && <Route path="prizes/:prizeId" element={<PrizeRoute />} />}
              <Route path="donate" element={<DonateRoute />} />
              <Route index element={<NotFound />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      )}
    </>
  );
};

export default App;
