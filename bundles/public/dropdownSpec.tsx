import React from 'react';

import Dropdown from './dropdown';
import { shallow } from 'enzyme';

describe('Dropdown', () => {
  let subject: ReturnType<typeof render>;
  describe('controlled', () => {
    let toggleSpy: jasmine.Spy;
    beforeEach(() => {
      toggleSpy = jasmine.createSpy('toggle');
      subject = render({ open: true, toggle: toggleSpy, children: <hr /> });
    });

    it('calls the toggle spy', () => {
      subject.find('img').simulate('click');
      expect(toggleSpy).toHaveBeenCalled();
    });

    it('shows children when open prop is true', () => {
      expect(subject.find('hr')).toExist();
    });

    it('hides children when open prop is false', () => {
      subject = render({ open: false, toggle: toggleSpy, children: <hr /> });
      expect(subject.find('hr')).not.toExist();
    });

    it('respects the closeOnClick flag', () => {
      subject.find('div').simulate('click');
      expect(toggleSpy).toHaveBeenCalled();
      toggleSpy.calls.reset();
      subject = render({ open: true, toggle: toggleSpy, closeOnClick: false, children: <hr /> });
      subject.find('div').simulate('click');
      expect(toggleSpy).not.toHaveBeenCalled();
    });
  });

  describe('uncontrolled', () => {
    it('toggles its own state', () => {
      subject = render({ children: <hr /> });
      expect(subject.find('hr')).not.toExist();
      subject.find('img').simulate('click');
      subject.update();
      expect(subject.find('hr')).toExist();
      subject.find('img').simulate('click');
      subject.update();
      expect(subject.find('hr')).not.toExist();
    });

    it('uses initiallyOpen', () => {
      subject = render({ initiallyOpen: true, children: <hr /> });
      expect(subject.find('hr')).toExist();
    });
  });

  function render(props = {}) {
    return shallow(<Dropdown {...props} />);
  }
});
