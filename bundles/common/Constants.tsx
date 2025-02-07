import React, { useContext } from 'react';

export const DefaultConstants = {
  PRIVACY_POLICY_URL: '',
  SWEEPSTAKES_URL: '',
  ANALYTICS_URL: '',
  API_ROOT: '',
  APIV2_ROOT: '',
  ADMIN_ROOT: '',
  STATIC_URL: '/static/',
  PAGINATION_LIMIT: 0,
};

const Constants = React.createContext(DefaultConstants);

export function useConstants() {
  return useContext(Constants);
}

export default Constants;
