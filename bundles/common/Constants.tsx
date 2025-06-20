import React from 'react';

export const DefaultConstants = {
  PRIVACY_POLICY_URL: '',
  SWEEPSTAKES_URL: '',
  ANALYTICS_URL: '',
  APIV2_ROOT: '',
  ADMIN_ROOT: '',
  STATIC_URL: '/static/',
  PAGINATION_LIMIT: 0,
  PAYPAL_MAXIMUM_AMOUNT: 0,
  ROOT_PATH: '',
};

const Constants = React.createContext(DefaultConstants);

export function useConstants() {
  return React.useContext(Constants);
}

export default Constants;
