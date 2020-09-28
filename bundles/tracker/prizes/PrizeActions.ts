import _ from 'lodash';

import { ActionTypes } from '../Action';
import { SafeDispatch } from '../hooks/useDispatch';
import * as CurrencyUtils from '../../public/util/currency';
import * as HTTPUtils from '../../public/util/http';
import TimeUtils from '../../public/util/TimeUtils';
import { Run } from '../runs/RunTypes';
import { Prize, PrizeSearchFilter } from './PrizeTypes';
import { ExtraArguments, StoreState } from '../Store';

function runFromNestedAPIRun(prefix: string, fields: { [field: string]: any }): Run | undefined {
  const runFields: { [field: string]: any } = {};
  for (const [field, value] of Object.entries(fields)) {
    if (field.startsWith(prefix)) {
      runFields[field.replace(prefix, '')] = value;
    }
  }

  // If no fields with the prefix were present, assume no run was specified.
  if (_.size(runFields) === 0) return undefined;

  return {
    name: runFields.name,
    canonicalUrl: runFields.canoncial_url,
    displayName: runFields.display_name,
    twitchName: runFields.twitch_name,
    public: runFields.public,
    category: runFields.category,
    description: runFields.description,
    console: runFields.console,
    releaseYear: runFields.release_year,
    deprecatedRunners: runFields.deprecated_runners,
    commentators: runFields.commentators,
    startTime: runFields.starttime != null ? TimeUtils.parseTimestamp(runFields.starttime) : undefined,
    endTime: runFields.endtime != null ? TimeUtils.parseTimestamp(runFields.endtime) : undefined,
    runTime: runFields.run_time,
    setupTime: runFields.setup_time,
    order: runFields.order,
    coop: runFields.coop,
    runners: runFields.runners,
    techNotes: runFields.techNotes,
    giantbombId: runFields.giantbomb_id != null ? runFields.giantbomb_id.toString() : undefined,
  };
}

function prizeFromAPIPrize({ pk, fields }: { pk: number; fields: { [field: string]: any } }): Prize {
  const category =
    fields.category != null
      ? {
          name: fields.category__name,
          public: fields.category__public,
        }
      : undefined;

  return {
    id: pk.toString(),
    name: fields.name,
    public: fields.public,
    description: fields.description,
    shortDescription: fields.shortdescription,
    canonicalUrl: fields.canonical_url,
    categoryId: fields.category != null ? fields.category.toString() : undefined,
    category,
    image: fields.image,
    altImage: fields.altimage,
    imageFile: fields.imagefile,
    extraInfo: fields.extrainfo,
    estimatedValue: CurrencyUtils.parseCurrency(fields.estimatedvalue),
    minimumBid: CurrencyUtils.parseCurrencyForced(fields.minimumbid),
    maximumBid: CurrencyUtils.parseCurrency(fields.maximumbid),
    sumDonations: fields.sumdonations,
    randomDraw: fields.randomdraw,
    eventId: fields.event != null ? fields.event.toString() : undefined,
    startRunId: fields.startrun != null ? fields.startrun.toString() : undefined,
    startRun: runFromNestedAPIRun('startrun__', fields),
    endRunId: fields.endrun != null ? fields.endrun.toString() : undefined,
    endRun: runFromNestedAPIRun('endrun__', fields),
    startTime: fields.starttime != null ? TimeUtils.parseTimestamp(fields.starttime) : undefined,
    endTime: fields.endtime != null ? TimeUtils.parseTimestamp(fields.endtime) : undefined,
    startDrawTime: fields.start_draw_time != null ? TimeUtils.parseTimestamp(fields.start_draw_time) : undefined,
    endDrawTime: fields.end_draw_time != null ? TimeUtils.parseTimestamp(fields.end_draw_time) : undefined,
    provider: fields.provider !== '' ? fields.provider : undefined,
    handlerId: fields.handler != null ? fields.handler.toString() : undefined,
    creator: fields.creator,
    creatorEmail: fields.creatoremail,
    creatorWebsite: fields.creatorwebsite,
    requiresShipping: fields.requiresshipping,
    customCountryFilter: fields.custom_country_filter,
    keyCode: fields.key_code,
    allowedPrizeCountries: fields.allowed_prize_countries.map((country: any) => country.toString()),
    disallowedPrizeRegions: fields.disallowed_prize_regions.map((country: any) => country.toString()),
    maxWinners: fields.maxwinners,
    maxMultiWin: fields.maxmultiwin,
    numWinners: parseInt(fields.numwinners),
  };
}

export function fetchPrizes(filter: PrizeSearchFilter = {}) {
  return (dispatch: SafeDispatch, getState: () => StoreState, { apiRoot }: ExtraArguments) => {
    dispatch({ type: ActionTypes.FETCH_PRIZES_STARTED });

    if (filter.event && /\D/.test(filter.event)) {
      filter.eventshort = filter.event;
      delete filter.event;
    }

    return HTTPUtils.get(`${apiRoot}search/`, { ...filter, type: 'prize' })
      .then((data: any[]) => {
        const prizes = data.map(prizeFromAPIPrize);

        dispatch({
          type: ActionTypes.FETCH_PRIZES_SUCCESS,
          prizes,
        });
      })
      .catch(error => {
        dispatch({
          type: ActionTypes.FETCH_PRIZES_FAILED,
        });
      });
  };
}
