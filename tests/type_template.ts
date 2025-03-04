/* eslint-disable @typescript-eslint/no-unused-vars */

import {
  AdPatch,
  AdPost,
  BidGet,
  BidPatch,
  BidPost,
  DonationCommentPatch,
  DonationGet,
  DonorGet,
  EventGet,
  InterviewGet,
  InterviewPatch,
  InterviewPost,
  MilestoneGet,
  MilestonePatch,
  MilestonePost,
  Model,
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
} from '@gamesdonequick/donation-tracker-api-types';

interface Response {
  status_code: number;
  data: PaginationInfo | Model;
}

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
let commentPatch: DonationCommentPatch;
