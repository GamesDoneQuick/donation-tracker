import SturdyWebSocket from 'sturdy-websocket';
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

import { trackerApi } from '@public/apiv2/reducers/trackerApi';
import { Tags } from '@public/apiv2/reducers/trackerBaseApi';
import { ForceArray, forceArray, MaybePromise } from '@public/util/Types';

import { getRoot, RootShape } from './apiRoot';
import { Dispatch } from './types';

const internal = Symbol('tracker_internal');

function socketUrl(url: string) {
  url = new URL(url, window.location.origin).toString();
  if (/^https?:\/\//.test(url)) {
    url = url.replace(/^http/, 'ws');
  }
  return url;
}

export function getSocketPath(apiOrState: { getState: () => unknown } | { apiRoot: RootShape }, path: string) {
  const r = 'getState' in apiOrState ? getRoot(apiOrState) : apiOrState.apiRoot.root;
  if (r == null) {
    throw new Error('insanity');
  }
  return socketUrl(`${r}/../../ws/${path}/`.replace(/\/\/+/g, '/'));
}

type SocketCallbacks = {
  socket: SturdyWebSocket;
  callbacks: ((ev: MessageEvent) => MaybePromise<void>)[];
  tags: ForceArray<Tags>;
};
const sockets: Record<string, SocketCallbacks> = {};

function newSocket(url: string) {
  const socket = new SturdyWebSocket(url, {
    shouldReconnect: ev => !ev.wasClean,
  });
  socket.addEventListener('message', async ev => await Promise.allSettled(sockets[url].callbacks.map(cb => cb(ev))));
  return socket;
}

/*
 * looks for an existing socket at the specified url, creates one if none exist, and sets up callbacks to track the
 * state of the socket in the Redux store as well as optionally invalidating query tags if the socket has to reconnect
 * to ensure that the data stays in sync
 */
async function getSocket(url: string, dispatch: Dispatch, tags: Tags = []) {
  let socket = sockets[url]?.socket;
  if (socket == null || socket.readyState === WebSocket.CLOSING || socket.readyState === WebSocket.CLOSED) {
    socket = newSocket(url);
    dispatch(socketsSlice.actions.setState([internal, { [url]: socket.readyState }]));
    socket.addEventListener('open', () => {
      dispatch(socketsSlice.actions.setState([internal, { [url]: WebSocket.OPEN }]));
    });
    socket.addEventListener('reopen', () => {
      dispatch(socketsSlice.actions.setState([internal, { [url]: WebSocket.OPEN }]));
      dispatch(trackerApi.util.invalidateTags(sockets[url].tags));
    });
    socket.addEventListener('close', () => {
      dispatch(socketsSlice.actions.setState([internal, { [url]: WebSocket.CLOSED }]));
    });
    socket.addEventListener('down', () => {
      dispatch(socketsSlice.actions.setState([internal, { [url]: WebSocket.CONNECTING }]));
    });
    sockets[url] = { socket, callbacks: [], tags: [] };
  }
  /* merge any new tags in
     one caveat is that this never clears old tags until the socket is completely closed, but this is harmless if
     nothing is listening for those tags, as invalidating a tag that nobody is subscribed to is a no-op */
  sockets[url].tags = [...new Set([...sockets[url].tags, ...forceArray(tags)])];
  if (socket.readyState !== WebSocket.OPEN) {
    // TODO: does this ever happen with SturdyWebSocket? maybe if the network is disabled?
    await new Promise<void>((resolve, reject) => {
      function open() {
        socket.removeEventListener('open', open);
        socket.removeEventListener('close', close);
        resolve();
      }

      function close() {
        socket.removeEventListener('open', open);
        socket.removeEventListener('close', close);
        reject();
      }

      socket.addEventListener('open', open);
      socket.addEventListener('close', close);
    });
  }
  return sockets[url];
}

export async function addCallback(
  url: string,
  dispatch: Dispatch,
  callback: (ev: MessageEvent) => void,
  tags: Tags = [],
) {
  const socket = await getSocket(url, dispatch, tags);
  socket.callbacks.push(callback);
  return () => {
    sockets[url].callbacks = sockets[url].callbacks.filter(c => c !== callback);
    if (sockets[url].callbacks.length === 0) {
      sockets[url].socket.close();
      delete sockets[url];
      dispatch(socketsSlice.actions.remState([internal, url]));
    }
  };
}

interface SocketShape {
  [url: string]: number;
}

const socketsSlice = createSlice({
  name: 'sockets',
  initialState: (): SocketShape => ({}),
  reducers: {
    setState(state, { payload: [i, entry] }: PayloadAction<[typeof internal, SocketShape]>) {
      if (i !== internal) {
        throw new Error('internal use only');
      }
      return { ...state, ...entry };
    },
    remState(state, { payload: [i, key] }: PayloadAction<[typeof internal, string]>) {
      if (i !== internal) {
        throw new Error('internal use only');
      }
      delete state[key];
    },
  },
});

// actions are internal use only

export const { reducerPath: socketsReducerPath, reducer: socketsReducer } = socketsSlice;
