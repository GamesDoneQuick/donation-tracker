import * as React from 'react';
import * as ReactDOM from 'react-dom';
import { Provider } from 'react-redux';
import _ from 'lodash';

import ErrorBoundary from '../public/errorBoundary';
import * as CurrencyUtils from '../public/util/currency';
import ThemeProvider from '../uikit/ThemeProvider';
import DonationForm from './donation/components/DonationForm';
import * as DonationActions from './donation/DonationActions';
import * as EventDetailsActions from './event_details/EventDetailsActions';
import useDispatch from './hooks/useDispatch';
import { store } from './Store';

/*
  AppInitializer acts as a proxy for bringing the preloaded props provided
  directly by the page on load into the Redux store for the app to run.
  Effectively, this simulates componentDidMount API requests for the same
  information, and is here to abstract that implementation to make conversion
  to a fully-API-powered frontend easier later on.
*/

// TODO: refine this with a complete typing of the initial payload.
type AppInitializerProps = { [prop: string]: any };

const AppInitializer = (props: AppInitializerProps) => {
  const {
    // EventDetails
    incentives,
    prizes,
    event: { receivername: receiverName },
    prizesUrl,
    rulesUrl,
    donateUrl,
    minimumDonation = 1,
    maximumDonation = Infinity,
    step = 0.01,
    // Donation
    initialForm,
  } = props;

  const dispatch = useDispatch();

  React.useEffect(() => {
    dispatch(DonationActions.loadDonation(initialForm));
  }, [dispatch, initialForm]);

  React.useEffect(() => {
    // TODO: refine this with a complete typing of the initial payload.
    const transformedIncentives = incentives.map((incentive: any) => {
      return {
        ...incentive,
        amount: CurrencyUtils.parseCurrency(incentive.amount) || 0.0,
        goal: CurrencyUtils.parseCurrency(incentive.goal),
      };
    });

    dispatch(
      EventDetailsActions.loadEventDetails({
        receiverName,
        prizesUrl,
        rulesUrl,
        donateUrl,
        minimumDonation,
        maximumDonation,
        step,
        availableIncentives: _.keyBy(transformedIncentives, 'id'),
        prizes,
      }),
    );
  }, [dispatch, event, prizesUrl, rulesUrl, donateUrl, minimumDonation, maximumDonation, step, incentives, prizes]);

  return null;
};

type DonateAppProps = {
  csrfToken: string;
  onSubmit: () => void;
};

window.DonateApp = (props: DonateAppProps) => {
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
