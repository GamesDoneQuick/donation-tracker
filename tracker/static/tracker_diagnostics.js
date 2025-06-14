let celeryTestWebsocket;
let pingWebsocket;

/* eslint-disable no-console,@typescript-eslint/no-unused-vars,no-unused-vars */

function togglePingWebsocket(url) {
  let interval;
  let counter = 0;

  function ping() {
    pingWebsocket.send('PING');
  }

  if (!pingWebsocket || pingWebsocket.readyState === WebSocket.CLOSING || pingWebsocket.readyState === WebSocket.CLOSED) {
    pingWebsocket = new WebSocket(url);

    document.getElementById('ping_status').textContent = 'Opening';

    pingWebsocket.addEventListener('open', function(event) {
      console.log('open', event);
      document.getElementById('ping_status').textContent = 'Opened';
      interval = setInterval(ping, 1000);
    });

    pingWebsocket.addEventListener('error', function(event) {
      console.log('error', event);
      document.getElementById('ping_status').textContent = 'Error';
    });

    pingWebsocket.addEventListener('close', function(event) {
      console.log('close', event);
      document.getElementById('ping_status').textContent = `Closed (${event.wasClean ? 'Clean' : 'Dirty'})`;
      clearInterval(interval);
      counter = 0;
    });

    pingWebsocket.addEventListener('message', function(event) {
      console.log('message', event);
      counter += 1;
      document.getElementById('ping_counter').textContent = counter;
      const date = Date.parse(event.data);
      if (date) {
        document.getElementById('ping_timestamp').textContent = new Date(date).toString();
      } else {
        document.getElementById('ping_timestamp').textContent = `Invalid Date: ${event.data}`;
      }
    });
  } else if (pingWebsocket && (pingWebsocket.readyState === WebSocket.CONNECTING || pingWebsocket.readyState === WebSocket.OPEN)) {
    pingWebsocket.close();
  }
}

function sendTestCeleryTask(url) {
  let timeout;

  if (!celeryTestWebsocket || celeryTestWebsocket.readyState === WebSocket.CLOSING || celeryTestWebsocket.readyState === WebSocket.CLOSED) {
    celeryTestWebsocket = new WebSocket(url);

    document.getElementById('celery_status').textContent = 'Opening';
    document.getElementById('celery_result').textContent = 'Waiting...';

    celeryTestWebsocket.addEventListener('open', function(event) {
      console.log('open', event);
      document.getElementById('celery_status').textContent = 'Opened';
      celeryTestWebsocket.send('PING');
      timeout = setTimeout(() => {
        document.getElementById('celery_result').textContent = 'Timed Out?';
      }, 10000);
    });

    celeryTestWebsocket.addEventListener('error', function(event) {
      console.log('error', event);
      document.getElementById('celery_status').textContent = 'Error';
    });

    celeryTestWebsocket.addEventListener('close', function(event) {
      console.log('close', event);
      document.getElementById('celery_status').textContent = `Closed (${event.wasClean ? 'Clean' : 'Dirty'})`;
    });

    celeryTestWebsocket.addEventListener('message', function(event) {
      clearTimeout(timeout);
      console.log('message', event);
      let timestamp;
      try {
        timestamp = JSON.parse(event.data).timestamp;
      } catch {
        document.getElementById('celery_result').textContent = `Invalid JSON: ${event.data}`;
        return;
      }
      const date = Date.parse(timestamp);
      if (date) {
        document.getElementById('celery_result').textContent = new Date(date).toString();
      } else {
        document.getElementById('celery_result').textContent = `Invalid Timestamp: ${timestamp}`;
      }
      celeryTestWebsocket.close();
    });
  }
}
