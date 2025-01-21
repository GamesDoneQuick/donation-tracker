import {
  AdPatch,
  AdPost,
  APIModel,
  BidPatch,
  BidPost,
  DonationCommentPatch,
  InterviewPatch,
  InterviewPost,
  MilestonePatch,
  MilestonePost,
  PaginationInfo,
  PrizePatch,
  PrizePost,
  RunPatch,
  RunPost,
  TalentPatch,
  TalentPost,
} from '@public/apiv2/APITypes';

interface Response {
  status_code: number;
  data: PaginationInfo | APIModel;
}

let response: Response;
let prizePost: PrizePost;
let prizePatch: PrizePatch;
let milestonePost: MilestonePost;
let milestonePatch: MilestonePatch;
let bidPost: BidPost;
let bidPatch: BidPatch;
let runPost: RunPost;
let runPatch: RunPatch;
let adPost: AdPost;
let adPatch: AdPatch;
let interviewPost: InterviewPost;
let interviewPatch: InterviewPatch;
let talentPost: TalentPost;
let talentPatch: TalentPatch;
let commentPatch: DonationCommentPatch;
