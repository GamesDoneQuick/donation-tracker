import React from 'react';
import { shallow } from 'enzyme';

import { DefaultConstants } from '@common/Constants';

import Spinner from './spinner';

describe('Spinner', () => {
  let subject: ReturnType<typeof shallow>;

  describe('when spinning is true and imageFile is provided', () => {
    beforeEach(() => {
      subject = render({ spinning: true, imageFile: 'foo.png' }, <hr />);
    });

    it('renders an img with the imageFile prop', () => {
      expect(subject.find('img').prop('src')).toEqual(`${DefaultConstants.STATIC_URL}foo.png`);
    });

    it('does not render children', () => {
      expect(subject.find('hr')).not.toExist();
    });
  });

  describe('when spinning is false', () => {
    beforeEach(() => {
      subject = render({ spinning: false }, <hr />);
    });

    it('does not render an img', () => {
      expect(subject.find('img')).not.toExist();
    });

    it('renders children', () => {
      expect(subject.find('hr')).toExist();
    });
  });

  function render(props = {}, children: React.ReactNode = null) {
    const defaultProps = {
      children,
      imageFile: 'foo/bar.gif',
      spinning: true,
    };
    return shallow(<Spinner {...defaultProps} {...props} />);
  }
});
