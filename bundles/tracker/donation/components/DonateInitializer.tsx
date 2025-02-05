import * as React from 'react';
import _ from 'lodash';

import * as CurrencyUtils from '@public/util/currency';

import * as EventDetailsActions from '@tracker/event_details/EventDetailsActions';
import { Prize } from '@tracker/event_details/EventDetailsTypes';
import useDispatch from '@tracker/hooks/useDispatch';

import * as DonationActions from '../DonationActions';
import { Bid, DonationFormErrors } from '../DonationTypes';

/*
  DonateInitializer acts as a proxy for bringing the preloaded props provided
  directly by the page on load into the Redux store for the app to run.
  Effectively, this simulates componentDidMount API requests for the same
  information, and is here to abstract that implementation to make conversion
  to a fully-API-powered frontend easier later on.
*/

type Incentive = {
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
  accepted_number?: number;
  goal?: string;
  description: string;
};

type InitialIncentive = {
  bid?: number; // ? `bid` will be missing if it was invalid or has closed since the form was opened
  customoptionname: string;
  amount: string;
};

type DonateInitializerProps = {
  incentives: Incentive[];
  formErrors: DonationFormErrors;
  ROOT_PATH: string;
  initialForm: {
    requestedvisibility?: string;
    requestedalias?: string;
    requestedemail?: string;
    requestedsolicitemail?: string;
    amount?: string;
    comment?: string;
  };
  initialIncentives: InitialIncentive[];
  event: {
    paypalcurrency: string;
    receivername: string;
    receiver_solicitation_text: string;
    receiver_logo: string;
    receiver_privacy_policy: string;
  };
  step: number;
  minimumDonation: number;
  maximumDonation: number;
  donateUrl: string;
  prizes: Prize[];
  prizesUrl: string;
  csrfToken: string;
};

const DonateInitializer = (props: DonateInitializerProps) => {
  const {
    // EventDetails
    incentives,
    prizes,
    event,
    prizesUrl,
    donateUrl,
    minimumDonation = 1,
    maximumDonation = Infinity,
    step = 0.01,
    csrfToken,
    // Donation
    initialForm,
    initialIncentives,
    formErrors,
  } = props;

  const dispatch = useDispatch();

  React.useEffect(() => {
    // This transform is lossy and a little brittle, making the assumption that
    // to have submitted the form in the first place, the bid must have been
    // valid. The server will potentially strip `bid.bid` from invalid bids,
    // but `bid.amount` _should_ always be a valid currency string.
    const transformedBids = initialIncentives.map(bid => ({
      incentiveId: bid.bid,
      customoptionname: bid.customoptionname,
      amount: CurrencyUtils.parseCurrency(bid.amount)!,
    }));

    const transformedDonation = {
      ...initialForm,
      amount: CurrencyUtils.parseCurrency(initialForm.amount),
    };

    dispatch(DonationActions.loadDonation(transformedDonation, transformedBids as Bid[], formErrors));
  }, [dispatch, formErrors, initialForm, initialIncentives]);

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
        currency: event.paypalcurrency,
        receiverName: event.receivername,
        receiverLogo: event.receiver_logo,
        receiverPrivacyPolicy: event.receiver_privacy_policy,
        receiverSolicitationText: event.receiver_solicitation_text,
        prizesUrl,
        donateUrl,
        minimumDonation,
        maximumDonation,
        step,
        availableIncentives: _.keyBy(transformedIncentives, 'id'),
        prizes,
      }),
    );
  }, [dispatch, event, prizesUrl, donateUrl, minimumDonation, maximumDonation, step, incentives, prizes, csrfToken]);

  return null;
};

export default DonateInitializer;
