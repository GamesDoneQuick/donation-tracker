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

function checkStatus(response: Response) {
  if ((response.status >= 200 && response.status < 300) || response.status === 422) {
    return response;
  } else {
    throw response;
  }
}

function parseJSON(response: Response) {
  return response.json();
}

function skipsCSRF(method: string) {
  return /^(GET|HEAD|OPTIONS|TRACE)$/i.test(method);
}

function getDefaultHeaders(method: string) {
  const headers: { [header: string]: any } = {
    'Content-Type': 'application/json',
  };

  if (!skipsCSRF(method)) {
    headers['X-CSRFToken'] = Cookies.get('csrftoken');
  }

  return headers;
}

type GetOptions = {
  headers?: { [header: string]: any };
};

export const get = (url: string, queryParams: object, opts: GetOptions = {}) => {
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

type PostOptions = {
  headers?: { [header: string]: any };
  encoder?: typeof Encoders[keyof typeof Encoders];
};

export const post = (url: string, data: object, opts: PostOptions = {}) => {
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
