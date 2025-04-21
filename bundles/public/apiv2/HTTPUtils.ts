import axios, { AxiosRequestConfig, AxiosResponse } from 'axios';

const instance = axios.create();

// only so that we can mock it out in tests
export function getInstance() {
  if (window.jasmine == null) {
    throw new Error('not for production use');
  }
  return instance;
}

const alreadyPrefetched: string[] = [];

export function request<ResponseType, DataType = any>(config: AxiosRequestConfig) {
  return instance.request<ResponseType, AxiosResponse<ResponseType>, DataType>({
    ...config,
    adapter(config): Promise<AxiosResponse> {
      const fallback = axios.getAdapter(instance.defaults.adapter);
      let prefetch: any = document.getElementById('API_PREFETCH');
      if (prefetch) {
        const uri = instance.getUri(config);
        // only use it once
        if (!alreadyPrefetched.includes(uri)) {
          try {
            prefetch = JSON.parse(prefetch.textContent!);
            const data: ResponseType = prefetch[uri];
            if (data) {
              alreadyPrefetched.push(uri);
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
