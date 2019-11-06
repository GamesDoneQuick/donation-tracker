export type Bid = {
  incentiveId: number;
  amount: string;
  customoptionname: string;
};

export type Incentive = {
  id: number;
  amount: number;
  name: string;
  customOption: string;
  parent?: {
    id: number;
    name: string;
    custom: boolean;
    maxlength: number;
    description: string;
  };
  runname: string;
  count: number;
  goal: number;
  description: string;
};

export type IncentivesAction =
  | {
      type: 'LOAD_INCENTIVES';
      incentives: Array<Incentive>;
    }
  | {
      type: 'CREATE_BID';
      bid: Bid;
    }
  | {
      type: 'DELETE_BID';
      incentiveId: number;
    };
