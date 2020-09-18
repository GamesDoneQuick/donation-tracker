import Spinner from './spinner';
import { shallow } from 'enzyme';
import React from 'react';
import { DefaultGlobals } from '../common/Globals';

describe('Spinner', () => {
  let subject: ReturnType<typeof shallow>;

  describe('when spinning is true and imageFile is provided', () => {
    beforeEach(() => {
      subject = render({ spinning: true, imageFile: 'foo.png' }, <hr />);
    });

    it('renders an img with the imageFile prop', () => {
      expect(subject.find('img').prop('src')).toEqual(`${DefaultGlobals.STATIC_URL}foo.png`);
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
