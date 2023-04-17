import React from 'react';
import { render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import Dropdown from './dropdown';

describe('Dropdown', () => {
  let subject: ReturnType<typeof renderComponent>;
  describe('controlled', () => {
    let toggleSpy: jasmine.Spy;
    beforeEach(() => {
      toggleSpy = jasmine.createSpy('toggle');
      subject = renderComponent({ open: true, toggle: toggleSpy, children: <hr /> });
    });

    it('calls the toggle spy', () => {
      userEvent.click(subject.getByRole('img'));
      expect(toggleSpy).toHaveBeenCalled();
    });

    it('shows children when open prop is true', () => {
      expect(subject.getByRole('separator')).not.toBeNull();
    });

    it('hides children when open prop is false', () => {
      subject = renderComponent({ open: false, toggle: toggleSpy, children: <div data-testid="dropdown-content" /> });
      expect(subject.queryByTestId('dropdown-content')).toBeNull();
    });

    it('respects the closeOnClick flag', () => {
      userEvent.click(subject.container.querySelector('div')!);
      expect(toggleSpy).toHaveBeenCalled();
      toggleSpy.calls.reset();
      subject = renderComponent({ open: true, toggle: toggleSpy, closeOnClick: false, children: <hr /> });
      userEvent.click(subject.container.querySelector('div')!);
      expect(toggleSpy).not.toHaveBeenCalled();
    });
  });

  describe('uncontrolled', () => {
    it('toggles its own state', () => {
      subject = renderComponent({ children: <hr /> });
      expect(subject.queryByRole('separator')).toBeNull();
      userEvent.click(subject.getByRole('img'));
      expect(subject.queryByRole('separator')).not.toBeNull();
      userEvent.click(subject.getByRole('img'));
      expect(subject.queryByRole('separator')).toBeNull();
    });

    it('uses initiallyOpen', () => {
      subject = renderComponent({ initiallyOpen: true, children: <hr /> });
      expect(subject.getByRole('separator')).not.toBeNull();
    });
  });

  function renderComponent(props = {}) {
    return render(<Dropdown {...props} />);
  }
});
