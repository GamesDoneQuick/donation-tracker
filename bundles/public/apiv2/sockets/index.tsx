import { ProcessingSocketImpl } from './ProcessingSocket';

let socketRoot: string | undefined;
let processingSocket: ProcessingSocketImpl | undefined;

function getAbsoluteSocketURL(path: string) {
  if (socketRoot == null) {
    throw 'setSocketRoot must be called with a value for the common websocket path before requesting a websocket.';
  }

  // If the root doesn't start with a slash, assume it's a fully-formed URL already.
  if (!socketRoot.startsWith('/')) return socketRoot;

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

  return `${protocol}//${window.location.host}${socketRoot}${path}`;
}

export const sockets = new (class {
  setSocketRoot(path: string) {
    socketRoot = path;
  }

  get processingSocket(): ProcessingSocketImpl {
    processingSocket ??= new ProcessingSocketImpl(getAbsoluteSocketURL('processing/'));
    return processingSocket;
  }
})();
