import axios, { AxiosRequestConfig } from 'axios';

const instance = axios.create();

// only so that we can mock it out in tests
export function getInstance() {
  if (process.env.NODE_ENV === 'PRODUCTION') {
    throw new Error('not for production use');
  }
  return instance;
}

export function setAPIRoot(root: string) {
  instance.defaults.baseURL = root;
}

export function setCSRFToken(token: string) {
  instance.defaults.headers.common['X-CSRFToken'] = token;
}

export function get<ResponseType, QueryParams extends object = object>(path: string, queryParams?: QueryParams) {
  return instance.get<ResponseType>(path, { params: queryParams, paramsSerializer: { indexes: null } });
}

export function post<ResponseType>(path: string, data?: Record<string, unknown>) {
  return instance.post<ResponseType>(path, data);
}

export function put<ResponseType>(path: string, data?: Record<string, unknown>) {
  return instance.put<ResponseType>(path, data);
}

export function patch<ResponseType>(path: string, data?: Record<string, unknown>) {
  return instance.patch<ResponseType>(path, data);
}

export function del<ResponseType>(path: string) {
  return instance.delete<ResponseType>(path);
}

export function request<ResponseType>(config: AxiosRequestConfig) {
  return instance.request<ResponseType>(config);
}

export default {
  getInstance,
  setAPIRoot,
  setCSRFToken,
  get,
  post,
  put,
  patch,
  del,
  request,
};
