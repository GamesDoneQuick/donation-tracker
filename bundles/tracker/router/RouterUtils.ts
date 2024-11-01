// import { createBrowserHistory } from 'history';
import queryString from 'query-string';
import { NavigateOptions as NavOptions, useNavigate } from 'react-router';

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
  query?: Record<string, unknown>;
  hash?: string;
  state?: Record<string, unknown>;
};

export function createTrackerHistory(rootPath: string) {
  // history = createBrowserHistory({ basename: rootPath });
  //
  // // Re-apply browser-standard scrolling behavior on route transitions
  // history.listen((location, action) => {
  //   // If the user is navigating backwards, don't reset scroll.
  //   if (action === 'POP') return;
  //   window.scrollTo(0, 0);
  // });
  // return history;
}

export default {
  navigateTo(
    navigate: ReturnType<typeof useNavigate>,
    path: string,
    options: NavigateOptions = {},
    navOptions: NavOptions = {},
  ) {
    const { forceReload = false, query, hash, state } = options;

    let fullPath = path;
    if (query != null) {
      fullPath += `?${queryString.stringify(query)}`;
    }
    if (hash != null) {
      fullPath += `#${hash}`;
    }
    navigate(fullPath, { ...navOptions, state });

    if (forceReload) {
      window.location.reload();
    }
  },
};
