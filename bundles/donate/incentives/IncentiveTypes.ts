export type Bid = {
  incentiveId: number;
  amount: number;
  customoptionname?: string;
};

export type Incentive = {
  id: number;
  name: string;
  customOption?: string;
  amount: number;
  parent?: {
    id: number;
    name: string;
    custom: boolean;
    maxlength: number;
    description: string;
  };
  runname: string;
  count?: number;
  goal?: number;
  description?: string;
  maxlength?: number;
  custom?: boolean;
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
