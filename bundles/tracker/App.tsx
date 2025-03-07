import React from 'react';
import { useParams } from 'react-router';
import { BrowserRouter, Route, Routes } from 'react-router-dom';

import { useConstants } from '@common/Constants';

import Donate from '@tracker/donation/components/Donate';
import Prize from '@tracker/prizes/components/Prize';
import Prizes from '@tracker/prizes/components/Prizes';

import { AnalyticsEvent, setAnalyticsURL, track } from './analytics/Analytics';
import DonateInitializer from './donation/components/DonateInitializer';
import NotFound from './router/components/NotFound';
import { setAPIRoot } from './Endpoints';

function PrizesRoute() {
  const { eventId } = useParams();
  return <Prizes eventId={eventId!} />;
}

function PrizeRoute() {
  const { prizeId } = useParams();
  return <Prize prizeId={prizeId!} />;
}

function DonateRoute() {
  const { eventId } = useParams();
  return <Donate eventId={eventId!} />;
}

const App = (props: React.ComponentProps<typeof DonateInitializer>) => {
  const { ANALYTICS_URL, API_ROOT } = useConstants();
  const [ready, setReady] = React.useState(false);

  React.useEffect(() => {
    setAPIRoot(API_ROOT);
    setAnalyticsURL(ANALYTICS_URL);
    setReady(true);
  }, [API_ROOT, ANALYTICS_URL]);

  React.useLayoutEffect(() => {
    track(AnalyticsEvent.TRACKER_APP_LOADED, {
      react_render_finished_ms: Math.floor(window.performance.now()),
    });
  }, []);

  const { SWEEPSTAKES_URL } = useConstants();

  return (
    <>
      {ready && (
        <BrowserRouter basename={props.ROOT_PATH}>
          <Routes>
            <Route path="events/:eventId">
              {SWEEPSTAKES_URL && <Route path="prizes" element={<PrizesRoute />} />}
              {SWEEPSTAKES_URL && <Route path="prizes/:prizeId" element={<PrizeRoute />} />}
              <Route path="donate" element={<DonateRoute />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      )}
    </>
  );
};

export default App;
