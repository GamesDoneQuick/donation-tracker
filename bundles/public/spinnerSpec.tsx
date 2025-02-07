import React from 'react';
import { render } from '@testing-library/react';

import Spinner from './spinner';

describe('Spinner', () => {
  let subject: ReturnType<typeof renderComponent>;

  describe('when spinning is true and partial is false', () => {
    beforeEach(() => {
      subject = renderComponent({ spinning: true }, <hr />);
    });

    it('renders a spinner', () => {
      expect(subject.baseElement.querySelector('.fa.fa-spinner')).not.toBeNull();
    });

    it('does not render children', () => {
      expect(subject.queryByRole('separator')).toBeNull();
    });
  });

  describe('when spinning is true and partial is true', () => {
    beforeEach(() => {
      subject = renderComponent({ spinning: true, showPartial: true }, <hr />);
    });

    it('renders a spinner', () => {
      expect(subject.baseElement.querySelector('.fa.fa-spinner')).not.toBeNull();
    });

    it('renders children', () => {
      expect(subject.getByRole('separator')).not.toBeNull();
    });
  });

  describe('when spinning is false', () => {
    beforeEach(() => {
      subject = renderComponent({ spinning: false }, <hr />);
    });

    it('does not render a spinner', () => {
      expect(subject.baseElement.querySelector('.fa.fa-spinner')).toBeNull();
    });

    it('renders children', () => {
      expect(subject.getByRole('separator')).not.toBeNull();
    });
  });

  function renderComponent(
    props: Omit<Partial<React.ComponentProps<typeof Spinner>>, 'children'> = {},
    children: React.ReactNode = null,
  ) {
    const defaultProps: React.ComponentProps<typeof Spinner> = {
      children,
      spinning: true,
    };
    return render(<Spinner {...defaultProps} {...props} />);
  }
});
