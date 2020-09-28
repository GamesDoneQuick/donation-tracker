export {};

declare global {
  // TODO: use a constants context instead of window globals
  interface Window {
    ROOT_PATH: string;
    API_ROOT: string;
    AdminApp: any;
    TrackerApp: any;
  }
}
