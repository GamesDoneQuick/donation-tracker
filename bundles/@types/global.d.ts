export {};

declare global {
  // TODO: use a constants context instead of window globals
  interface Window {
    PRIVACY_POLICY_URL: string;
    SWEEPSTAKES_URL: string;
    ROOT_PATH: string;
    STATIC_URL: string;
    APP_NAME: string;
    API_ROOT: string;
    AdminApp: any;
    TrackerApp: any;
  }
}
