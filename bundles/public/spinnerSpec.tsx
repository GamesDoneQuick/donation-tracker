import React from 'react';
import { render } from '@testing-library/react';

import { DefaultConstants } from '@common/Constants';

import Spinner from './spinner';

describe('Spinner', () => {
  let subject: ReturnType<typeof renderComponent>;

  describe('when spinning is true and imageFile is provided', () => {
    beforeEach(() => {
      subject = renderComponent({ spinning: true, imageFile: 'foo.png' }, <hr />);
    });

    it('renders an img with the imageFile prop', () => {
      expect(subject.queryByRole('img')?.getAttribute('src')).toEqual(`${DefaultConstants.STATIC_URL}foo.png`);
    });

    it('does not render children', () => {
      expect(subject.queryByRole('separator')).toBeNull();
    });
  });

  describe('when spinning is false', () => {
    beforeEach(() => {
      subject = renderComponent({ spinning: false }, <hr />);
    });

    it('does not render an img', () => {
      expect(subject.queryByRole('img')).toBeNull();
    });

    it('renders children', () => {
      expect(subject.getByRole('separator')).not.toBeNull();
    });
  });

  function renderComponent(props = {}, children: React.ReactNode = null) {
    const defaultProps = {
      children,
      imageFile: 'foo/bar.gif',
      spinning: true,
    };
    return render(<Spinner {...defaultProps} {...props} />);
  }
});
