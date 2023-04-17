import React from 'react';
import { render } from '@testing-library/react';

import ErrorList from './errorList';

describe('ErrorList', () => {
  it('displays nothing if given a nullish value', () => {
    expect(render(<ErrorList />).container.innerHTML).toEqual('');
  });

  it('displays nothing if given an empty array', () => {
    expect(render(<ErrorList errors={[]} />).container.innerHTML).toEqual('');
  });

  it('displays a node for each error provided', async () => {
    expect(render(<ErrorList errors={['1', '2']} />).queryAllByRole('listitem').length).toBe(2);
  });
});
