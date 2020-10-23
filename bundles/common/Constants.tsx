import React, { useContext } from 'react';

export const DefaultConstants = {
  PRIVACY_POLICY_URL: '',
  SWEEPSTAKES_URL: '',
  API_ROOT: '',
  ADMIN_ROOT: '',
  STATIC_URL: '/static/',
  CSRF_TOKEN: '',
};

const Constants = React.createContext(DefaultConstants);

export function useConstants() {
  return useContext(Constants);
}

export default Constants;
