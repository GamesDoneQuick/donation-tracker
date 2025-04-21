import axios, { AxiosRequestConfig, AxiosResponse } from 'axios';

const instance = axios.create();

// only so that we can mock it out in tests
export function getInstance() {
  if (window.jasmine == null) {
    throw new Error('not for production use');
  }
  return instance;
}

export function resetPrefetch() {
  if (window.jasmine == null) {
    throw new Error('not for production use');
  }
  usedPrefetch.splice(0, usedPrefetch.length);
}

const usedPrefetch: string[] = [];

export function request<ResponseType, DataType = any>(config: AxiosRequestConfig) {
  return instance.request<ResponseType, AxiosResponse<ResponseType>, DataType>({
    ...config,
    adapter(config): Promise<AxiosResponse> {
      const fallback = axios.getAdapter(instance.defaults.adapter);
      const prefetch = document.getElementById('API_PREFETCH');
      if (prefetch) {
        const uri = instance.getUri(config);
        // only use it once
        if (!usedPrefetch.includes(uri)) {
          try {
            const data: ResponseType = JSON.parse(prefetch.textContent!)[uri];
            if (data) {
              usedPrefetch.push(uri);
              return Promise.resolve({ data, status: 200, statusText: 'Found', headers: {}, config });
            }
          } catch {
            // nothing
          }
        }
      }
      return fallback(config);
    },
  });
}

export default {
  getInstance,
  request,
};
