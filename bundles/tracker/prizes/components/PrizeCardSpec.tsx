import * as React from 'react';
import PrizeCard from './PrizeCard';
import { mockState, mountWithState } from '../../../../spec/Suite';
import { getFixturePrize } from '../../../../spec/fixtures/Prize';

describe('PrizeCard', () => {
  let subject;

  beforeEach(() => {
    mockState({ prizes: { loading: false, prizes: { 123: getFixturePrize({ imageFile: 'foo' }) } } });
  });

  it('displays "No Image Found" if an error occurs while loading the image', () => {
    subject = render();

    subject.find('img').simulate('error');
    subject.update();
    expect(subject.find('img')).not.toExist();
    expect(subject.text()).toContain('No Image Provided');
  });

  function render(props = {}) {
    const defaultProps = {
      prizeId: '123',
    };

    return mountWithState(<PrizeCard {...defaultProps} {...props} />);
  }
});
