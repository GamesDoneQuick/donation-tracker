import * as React from 'react';
import * as ReactDOM from 'react-dom';
import { Provider, useDispatch } from 'react-redux';

import ErrorBoundary from '../public/errorBoundary';
import ThemeProvider from '../uikit/ThemeProvider';
import DonationForm from './donation/components/DonationForm';
import * as DonationActions from './donation/DonationActions';
import * as EventDetailsActions from './event_details/EventDetailsActions';
import * as IncentiveActions from './incentives/IncentiveActions';
import { store } from './reducer';

/*
  AppInitializer acts as a proxy for bringing the preloaded props provided
  directly by the page on load into the Redux store for the app to run.
  Effectively, this simulates componentDidMount API requests for the same
  information, and is here to abstract that implementation to make conversion
  to a fully-API-powered frontend easier later on.
*/

type AppInitializerProps = { [prop: string]: any };

const AppInitializer = (props: AppInitializerProps) => {
  const {
    // Incentives
    incentives,
    // EventDetails
    event,
    prizesUrl,
    rulesUrl,
    donateUrl,
    minimumDonation,
    maximumDonation,
    step,
    // Donation
    initialForm,
  } = props;

  const dispatch = useDispatch();

  React.useEffect(() => {
    dispatch(IncentiveActions.loadIncentives(incentives));
  }, [dispatch, incentives]);

  React.useEffect(() => {
    dispatch(DonationActions.loadDonation(initialForm));
  }, [dispatch, initialForm]);

  React.useEffect(() => {
    dispatch(
      EventDetailsActions.loadEventDetails({
        event,
        prizesUrl,
        rulesUrl,
        donateUrl,
        minimumDonation,
        maximumDonation,
        step,
      }),
    );
  }, [dispatch, event, prizesUrl, rulesUrl, donateUrl, minimumDonation, maximumDonation, step]);

  return null;
};

window.DonateApp = function(props: AppInitializerProps) {
  ReactDOM.render(
    <Provider store={store}>
      <AppInitializer {...props} />
      <ThemeProvider>
        <ErrorBoundary>
          <DonationForm {...props} />
        </ErrorBoundary>
      </ThemeProvider>
    </Provider>,
    document.getElementById('container'),
  );
};
