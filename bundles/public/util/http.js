import Cookies from './cookies';
import queryString from 'query-string';

export const Encoders = {
  JSON: {
    module: JSON,
    contentType: 'application/json',
  },
  QUERY: {
    module: queryString,
    contentType: 'application/x-www-form-urlencoded',
  },
};

function checkStatus(response) {
  if ((response.status >= 200 && response.status < 300) || response.status === 422) {
    return response;
  } else {
    throw response;
  }
}

function parseJSON(response) {
  return response.json();
}

function skipsCSRF(method) {
  return /^(GET|HEAD|OPTIONS|TRACE)$/i.test(method);
}

function getDefaultHeaders(method) {
  const headers = {
    'Content-Type': 'application/json',
  };

  if (!skipsCSRF(method)) {
    headers['X-CSRFToken'] = Cookies.get('csrftoken');
  }

  return headers;
}

export const get = (url, queryParams, opts = {}) => {
  const { headers } = opts;
  const query = queryParams ? '?' + queryString.stringify(queryParams) : '';

  return fetch(`${url}${query}`, {
    method: 'GET',
    headers: {
      ...getDefaultHeaders('GET'),
      ...headers,
    },
  })
    .then(checkStatus)
    .then(parseJSON);
};

export const post = (url, data, opts = {}) => {
  const { headers, encoder = Encoders.JSON } = opts;

  return fetch(url, {
    method: 'POST',
    headers: {
      ...getDefaultHeaders('POST'),
      'Content-Type': encoder.contentType,
      ...headers,
    },
    body: encoder.module.stringify(data),
  })
    .then(checkStatus)
    .then(parseJSON);
};

export default {
  get,
  post,
  Encoders,
};
