import React from 'react';
import { Provider } from 'react-redux';
import { Route, Routes } from 'react-router';
import { StaticRouter } from 'react-router-dom/server';
import { fireEvent, render } from '@testing-library/react';

import { processPrize } from '@public/apiv2/Processors';
import { store } from '@public/apiv2/Store';

import { getFixturePrize } from '@spec/fixtures/Prize';

import PrizeCard from './PrizeCard';

describe('PrizeCard', () => {
  let subject;

  it('displays "No Image Found" if an error occurs while loading the image', () => {
    subject = renderComponent();

    fireEvent.error(subject.queryByRole('img')!);
    expect(subject.queryByRole('img')).toBeNull();
    expect(subject.getByText('No Image Provided')).not.toBeNull();
  });

  function renderComponent(props: Partial<React.ComponentProps<typeof PrizeCard>> = {}) {
    const defaultProps = {
      prize: processPrize(getFixturePrize()),
      currency: 'USD',
    };

    const prize = props.prize || defaultProps.prize;

    return render(
      <Provider store={store}>
        <StaticRouter location={`/${prize.event}`}>
          <Routes>
            <Route path="/:eventId" element={<PrizeCard {...defaultProps} {...props} />} />
          </Routes>
        </StaticRouter>
      </Provider>,
    );
  }
});
