import ErrorList from './errorList';
import { shallow } from 'enzyme';
import React from 'react';

describe('ErrorList', () => {
  it('displays nothing if given a nullish value', () => {
    expect(shallow(<ErrorList />).isEmptyRender()).toBe(true);
  });

  it('displays nothing if given an empty array', () => {
    expect(shallow(<ErrorList errors={[]} />).isEmptyRender()).toBe(true);
  });

  it('displays a node for each error provided', () => {
    expect(shallow(<ErrorList errors={['1', '2']} />).find('li').length).toBe(2);
  });
});
