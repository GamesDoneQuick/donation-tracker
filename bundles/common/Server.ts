interface MessageDict {
  [key: string]: string[];
}

export interface ServerError {
  error: string;
  exception: string;
}

export interface ValidationError extends ServerError {
  message_dict: MessageDict;
}

export function isServerError(error: any): error is ServerError {
  return (
    error &&
    Object.prototype.hasOwnProperty.call(error, 'error') &&
    Object.prototype.hasOwnProperty.call(error, 'exception')
  );
}

export function isValidationError(error: ServerError): error is ValidationError {
  return Object.prototype.hasOwnProperty.call(error, 'message_dict');
}
