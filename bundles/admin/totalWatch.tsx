import * as React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useParams } from 'react-router';

import modelActions from '../public/api/actions/models';

function socketState(socket: WebSocket | null) {
  if (socket) {
    switch (socket.readyState) {
      case WebSocket.CONNECTING:
        return 'CONNECTING';
      case WebSocket.OPEN:
        return 'OPEN';
      case WebSocket.CLOSED:
        return 'CLOSED';
      case WebSocket.CLOSING:
        return 'CLOSING';
    }
  } else {
    return 'No Socket';
  }
}

export default React.memo(function TotalWatch() {
  const { event: eventId } = useParams();
  const event = useSelector((state: any) => state.models.event?.find((e: any) => e.pk === +eventId!));
  const dispatch = useDispatch();
  const retry = React.useRef<number>(0);
  const [socket, setSocket] = React.useState<WebSocket | null>(null);
  const connectWebsocket = React.useCallback(() => {
    const socket = new WebSocket(
      `${window.location.protocol.replace('http', 'ws')}//${window.location.host}/tracker/ws/donations/`,
    );

    socket.addEventListener('open', () => {
      dispatch(modelActions.loadModels('event', { id: eventId }));
      retry.current = 0;
    });

    socket.addEventListener('error', err => {
      console.error(err);
      retry.current += 1;
    });

    socket.addEventListener('close', () => {
      const delay = Math.min(Math.pow(2.0, retry.current), 32);

      setTimeout(connectWebsocket, delay * 1000);
    });

    socket.addEventListener('message', () => {
      dispatch(modelActions.loadModels('event', { id: eventId }));
    });
    setSocket(socket);
  }, [dispatch, eventId]);
  React.useEffect(() => {
    connectWebsocket();
  }, [connectWebsocket]);

  return event?.amount ? (
    <>
      <div>Total: ${new Intl.NumberFormat().format(event.amount)}</div>
      <div>
        Socket State: {socketState(socket)} {retry.current > 0 && `(${retry.current})`}
      </div>
    </>
  ) : null;
});
