import * as React from 'react';

import { getFixturePrize } from '../../../../spec/fixtures/Prize';
import { mockState, mountWithState } from '../../../../spec/Suite';
import Prize from './Prize';

describe('Prize', () => {
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

    return mountWithState(<Prize {...defaultProps} {...props} />);
  }
});
