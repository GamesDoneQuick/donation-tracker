import { createBrowserHistory } from 'history';
import queryString from 'query-string';

export const APP_BASE_PATH = ((root?: string) => {
  if (root == null) return '';
  return root.endsWith('/') ? root.substring(0, root.length - 1) : root;
})(window.ROOT_PATH);

export const EXTERNAL_TRACKER_BASE_PATH = window;

export const Routes = {
  EVENT_BASE: (eventId: string | number) => `/events/${eventId}`,
  // TODO: This URL is currently inverted as other parts of the tracker have
  // expect it to be in this format. Once those dependencies can be updated,
  // this can change to match normal REST structure.
  EVENT_DONATE: (eventId: string | number) => `/donate/${eventId}`,
  EVENT_PRIZES: (eventId: string | number) => `/events/${eventId}/prizes`,
  EVENT_PRIZE: (eventId: string | number, prizeId: string | number) => `/events/${eventId}/prizes/${prizeId}`,
};

type NavigateOptions = {
  replace?: boolean;
  forceReload?: boolean;
  query?: object;
  hash?: string;
  state?: object;
};

export const history = createBrowserHistory({ basename: APP_BASE_PATH });

// Re-apply browser-standard scrolling behavior on route transitions
history.listen((location, action) => {
  // If the user is navigating backwards, don't reset scroll.
  if (action === 'POP') return;
  window.scrollTo(0, 0);
});

export default {
  history,

  getLocation: () => history.location,
  getLocationHash: () => history.location.hash.slice(1),

  navigateTo(pathname: string, options: NavigateOptions = {}) {
    const { replace = false, forceReload = false, query, hash, state } = options;

    const navigate = replace ? history.replace : history.push;

    let fullPath = pathname;
    if (query != null) {
      fullPath += `?${queryString.stringify(query)}`;
    }
    if (hash != null) {
      fullPath += `#${hash}`;
    }

    navigate(fullPath, state);

    if (forceReload) {
      window.location.reload();
    }
  },

  isLocalUrl(url: string) {
    return !/(?:^[a-z][a-z0-9+.-]*:|\/\/)/.test(url);
  },
};
