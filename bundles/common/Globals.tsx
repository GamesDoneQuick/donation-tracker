import React, { useContext } from 'react';

export const DefaultGlobals = {
  PRIVACY_POLICY_URL: '',
  SWEEPSTAKES_URL: '',
  API_ROOT: '',
  STATIC_URL: '/static/',
  CSRF_TOKEN: '',
};

const Globals = React.createContext(DefaultGlobals);

export function useGlobals() {
  return useContext(Globals);
}

export default Globals;
