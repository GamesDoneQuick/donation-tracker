import axios, { AxiosRequestConfig, AxiosResponse } from 'axios';

const instance = axios.create();

// only so that we can mock it out in tests
export function getInstance() {
  if (process.env.NODE_ENV === 'production') {
    throw new Error('not for production use');
  }
  return instance;
}

export function request<ResponseType, DataType = any>(config: AxiosRequestConfig) {
  return instance.request<ResponseType, AxiosResponse<ResponseType>, DataType>(config);
}

export default {
  getInstance,
  request,
};
