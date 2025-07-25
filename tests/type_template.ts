/* eslint-disable @typescript-eslint/no-unused-vars */

import {
  AdPatch,
  AdPost,
  APIModel,
  BidGet,
  BidPatch,
  BidPost,
  DonationCommentPatch,
  DonationGet,
  DonationPost,
  DonorGet,
  EventGet,
  InterviewGet,
  InterviewPatch,
  InterviewPost,
  MilestoneGet,
  MilestonePatch,
  MilestonePost,
  PaginationInfo,
  PrizeGet,
  PrizePatch,
  PrizePost,
  RunGet,
  RunPatch,
  RunPost,
  TalentGet,
  TalentPatch,
  TalentPost,
} from '@public/apiv2/APITypes';

type Response =
  | {
      status_code: 200 | 201;
      content_type: string;
      data: string | string[] | PaginationInfo<APIModel> | APIModel | { confirm_url: string };
    }
  | {
      status_code: 204;
    };

let response: Response;
let eventGet: EventGet;
let prizeGet: PrizeGet;
let prizePost: PrizePost;
let prizePatch: PrizePatch;
let milestoneGet: MilestoneGet;
let milestonePost: MilestonePost;
let milestonePatch: MilestonePatch;
let bidGet: BidGet;
let bidPost: BidPost;
let bidPatch: BidPatch;
let donorGet: DonorGet;
let runGet: RunGet;
let runPost: RunPost;
let runPatch: RunPatch;
let adPost: AdPost;
let adPatch: AdPatch;
let interviewGet: InterviewGet;
let interviewPost: InterviewPost;
let interviewPatch: InterviewPatch;
let talentGet: TalentGet;
let talentPost: TalentPost;
let talentPatch: TalentPatch;
let donationGet: DonationGet;
let donatePost: DonationPost;
let commentPatch: DonationCommentPatch;
