import { act, fireEvent, render, waitFor, waitForElementToBeRemoved, within } from '@testing-library/react';

export async function waitForSpinner(subject: ReturnType<typeof render>) {
  function spinner() {
    return subject.queryAllByTestId('spinner');
  }

  if (spinner().length) {
    await waitForElementToBeRemoved(spinner);
  }
}

export async function waitForAPIErrors(
  subject: ReturnType<typeof render>,
  { errorText = 'Request failed with status code 404', reset = true } = {},
) {
  // default handler is just a 404 but that's fine
  await waitFor(() => expect(subject.getByTestId('api-errors')).not.toBeNull());
  expect(subject.getByTestId('api-errors').innerText).toMatch(errorText);
  if (reset) {
    act(() => {
      fireEvent.click(getByChainedTestId(subject, 'api-errors', 'reset'));
    });
  }
}

export function getByChainedTestId(subject: ReturnType<typeof render>, ...ids: string[]) {
  let element: ReturnType<typeof subject.getByTestId> | null = null;
  if (ids.length === 0) {
    throw new Error('must provide at least one id');
  }
  while (ids.length) {
    element = (element ? within(element) : subject).getByTestId(ids[0]);
    ids = ids.slice(1);
  }
  return element!;
}

export function queryByChainedTestId(subject: ReturnType<typeof render>, ...ids: string[]) {
  let element: ReturnType<typeof subject.getByTestId> | null = null;
  if (ids.length === 0) {
    throw new Error('must provide at least one id');
  }
  while (ids.length) {
    if (ids.length > 1) {
      element = (element ? within(element) : subject).getByTestId(ids[0]);
    } else {
      element = (element ? within(element) : subject).queryByTestId(ids[0]);
    }
    ids = ids.slice(1);
  }
  return element;
}
