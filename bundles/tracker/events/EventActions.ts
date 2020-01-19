import { ActionTypes } from '../Action';
import Endpoints from '../Endpoints';
import { SafeDispatch } from '../hooks/useDispatch';
import * as CurrencyUtils from '../../public/util/currency';
import * as HTTPUtils from '../../public/util/http';
import TimeUtils from '../../public/util/TimeUtils';
import { Event, EventSearchFilter } from './EventTypes';

function eventFromAPIEvent({ pk, fields }: { pk: number; fields: { [field: string]: any } }): Event {
  return {
    id: pk.toString(),
    short: fields.short,
    name: fields.name,
    canonicalUrl: fields.canonical_url,
    public: fields.public,
    useOneStepScreening: fields.use_one_step_screening,
    receiverName: fields.receivername,
    scheduleId: fields.scheduleid != null ? fields.scheduleid.toString() : undefined,
    startTime: fields.startTime != null ? TimeUtils.parseTimestamp(fields.startTime) : undefined,
    timezone: fields.timezone,
    locked: fields.locked,
    paypalEmail: fields.paypalemail,
    paypalCurrency: fields.paypalcurrency,
    paypalImgurl: fields.paypalimgurl,
    targetAmount: CurrencyUtils.parseCurrencyForced(fields.targetamount),
    allowDonations: fields.allow_donations,
    minimumDonation: CurrencyUtils.parseCurrencyForced(fields.minimumdonation),
    autoApproveThreshold: CurrencyUtils.parseCurrency(fields.auto_approve_threshold),
    prizeCoordinator: fields.prizecoordinator || undefined,
    allowedPrizeCountries: fields.allowed_prize_countries,
    disallowedPrizeRegions: fields.disallowed_prize_regions,
    prizeAcceptDeadlineDelta: fields.prize_accept_deadline_delta,
    amount: CurrencyUtils.parseCurrencyForced(fields.amount),
    count: CurrencyUtils.parseCurrencyForced(fields.count),
    max: CurrencyUtils.parseCurrencyForced(fields.max),
    avg: CurrencyUtils.parseCurrency(fields.avg),
    donationEmailSender: fields.donationemailsender || undefined,
    donationEmailTemplate: fields.donationemailtemplate || undefined,
    pendingDonationEmailTemplate: fields.pendingdonationemailtemplate || undefined,
    prizeContributorEmailTemplate: fields.prizecontributoremailtemplate || undefined,
    prizeWinnerEmailTemplate: fields.prizewinneremailtemplate || undefined,
    prizeWinnerAcceptEmailTemplate: fields.prizewinneracceptemailtemplate || undefined,
    prizeShippedEmailTemplate: fields.prizeshippedemailtemplate || undefined,
  };
}

export function selectEvent(eventId: string) {
  return {
    type: ActionTypes.SELECT_EVENT,
    eventId,
  };
}

export function fetchEvents(filters: EventSearchFilter = {}) {
  return (dispatch: SafeDispatch) => {
    dispatch({ type: ActionTypes.FETCH_EVENTS_STARTED });

    return HTTPUtils.get(Endpoints.SEARCH, { ...filters, type: 'event' })
      .then((data: Array<any>) => {
        const events = data.map(eventFromAPIEvent);

        dispatch({
          type: ActionTypes.FETCH_EVENTS_SUCCESS,
          events,
        });
      })
      .catch(() => {
        dispatch({
          type: ActionTypes.FETCH_EVENTS_FAILED,
        });
      });
  };
}
