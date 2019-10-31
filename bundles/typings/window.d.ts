export {};

declare global {
  interface Window {
    ROOT_PATH: string;
    APP_NAME: string;
    API_ROOT: string;
    STATIC_URL: string;
    AdminApp: any;
    DonateApp: any;
  }
}
