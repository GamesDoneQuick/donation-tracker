import * as React from 'react';
import _ from 'lodash';

import * as CurrencyUtils from '../../../public/util/currency';
import * as EventDetailsActions from '../../event_details/EventDetailsActions';
import { Prize } from '../../event_details/EventDetailsTypes';
import useDispatch from '../../hooks/useDispatch';
import RouterUtils from '../../router/RouterUtils';
import * as DonationActions from '../DonationActions';
import { Bid } from '../DonationTypes';

/*
  DonateInitializer acts as a proxy for bringing the preloaded props provided
  directly by the page on load into the Redux store for the app to run.
  Effectively, this simulates componentDidMount API requests for the same
  information, and is here to abstract that implementation to make conversion
  to a fully-API-powered frontend easier later on.
*/

type DonateInitializerProps = {
  incentives: Array<{
    id: number;
    parent: {
      id: number;
      name: string;
      custom: boolean;
      maxlength?: number;
      description: string;
    };
    name: string;
    runname: string;
    order: number;
    amount: string; // TODO: this and goal should be numbers but django seems to be serializing them as strings?
    count: number;
    goal?: string;
    description: string;
  }>;
  formErrors: {
    bidsform: Array<{
      bid: Array<string>;
    }>;
    commentform: object;
  };
  initialForm: {
    requestedvisibility?: string;
    requestedalias?: string;
    requestedemail?: string;
    requestedsolicitemail?: string;
    amount?: string;
    comment?: string;
  };
  initialIncentives: Array<{
    bid?: number; // ? `bid` will be null if it was closed
    customoptionname: string;
    amount: string;
  }>;
  event: {
    receivername: string;
  };
  step: number;
  minimumDonation: number;
  maximumDonation: number;
  donateUrl: string;
  prizes: Array<Prize>;
  prizesUrl: string;
  csrfToken: string;
};

const DonateInitializer = (props: DonateInitializerProps) => {
  const {
    // EventDetails
    incentives,
    prizes,
    event: { receivername: receiverName },
    prizesUrl,
    donateUrl,
    minimumDonation = 1,
    maximumDonation = Infinity,
    step = 0.01,
    csrfToken,
    // Donation
    initialForm,
    initialIncentives,
    formErrors: { bidsform: bidErrors },
  } = props;

  const dispatch = useDispatch();
  const urlHash = RouterUtils.getLocationHash();

  React.useEffect(() => {
    // This transform is lossy and a little brittle, making the assumption that
    // to have submitted the form in the first place, the bid must have been
    // valid. The server will potentially strip `bid.bid` from invalid bids,
    // but `bid.amount` _should_ always be a valid currency string.
    const transformedBids = initialIncentives
      .map(bid => ({
        incentiveId: bid.bid,
        customoptionname: bid.customoptionname,
        amount: CurrencyUtils.parseCurrency(bid.amount)!,
      }))
      .filter(bid => bid.incentiveId != null);

    const transformedDonation = {
      ...initialForm,
      amount: CurrencyUtils.parseCurrency(initialForm.amount),
    };

    const transformedError =
      bidErrors.length > 0 ? 'One or more of your chosen incentives is no longer available for bids.' : undefined;

    dispatch(DonationActions.loadDonation(transformedDonation, transformedBids as Array<Bid>, transformedError));
  }, [dispatch, initialForm]);

  React.useEffect(() => {
    const transformedIncentives = incentives.map(incentive => {
      return {
        ...incentive,
        amount: CurrencyUtils.parseCurrency(incentive.amount) || 0.0,
        goal: incentive.goal != null ? CurrencyUtils.parseCurrency(incentive.goal) : undefined,
      };
    });

    dispatch(
      EventDetailsActions.loadEventDetails({
        csrfToken,
        receiverName,
        prizesUrl,
        donateUrl,
        minimumDonation,
        maximumDonation,
        step,
        availableIncentives: _.keyBy(transformedIncentives, 'id'),
        prizes,
      }),
    );
  }, [dispatch, event, prizesUrl, donateUrl, minimumDonation, maximumDonation, step, incentives, prizes]);

  React.useEffect(() => {
    const presetAmount = CurrencyUtils.parseCurrency(urlHash);
    if (presetAmount != null) {
      dispatch(DonationActions.updateDonation({ amount: presetAmount }));
    }
  }, []);

  return null;
};

export default DonateInitializer;
