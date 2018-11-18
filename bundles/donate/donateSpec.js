import React from 'react';
import ReactDOM from 'react-dom';
import TestUtils from 'react-dom/test-utils';

import Donate from './donate';

describe('#Donate', () => {
  let subject;
  let formData;

  beforeEach(() => {
    subject = null;
    formData = null;
    if (!document.getElementById('container')) {
      const container = document.createElement('div', 'container');
      container.id = 'container';
      document.body.appendChild(container);
    }
    ReactDOM.render(
      <React.Fragment>
        <table data-form='bidsform' data-form-type='management'>
          <tbody>
          <tr>
            <td>
              <input id="id_bidsform-TOTAL_FORMS" name="bidsform-TOTAL_FORMS" type="hidden" value="1"/>
              <input id="id_bidsform-INITIAL_FORMS" name="bidsform-INITIAL_FORMS" type="hidden" value="0"/>
              <input id="id_bidsform-MIN_NUM_FORMS" name="bidsform-MIN_NUM_FORMS" type="hidden" value="0"/>
              <input id="id_bidsform-MAX_NUM_FORMS" name="bidsform-MAX_NUM_FORMS" type="hidden" value="10"/>
            </td>
          </tr>
          </tbody>
        </table>
        <table
          data-form='bidsform'
          data-form-type='empty'>
          <tbody>
          <tr>
            <td>
              <input
                id="id_bidsform-__prefix__-bid"
                name="bidsform-__prefix__-bid"
                className="mf_selection"
                type="hidden"
                value="None"/>
            </td>
            <td>
              <input id="id_bidsform-__prefix__-customoptionname" maxLength="64"
                     name="bidsform-__prefix__-customoptionname" type="text"/>
            </td>
            <td>
              <input
                className="cdonationbidamount"
                id="id_bidsform-__prefix__-amount"
                name="bidsform-__prefix__-amount"
                step="0.01"
                type="number"/>
            </td>
          </tr>
          </tbody>
        </table>
        <table data-form='prizesform' data-form-type='management'>
          <tbody>
          <tr>
            <td>
              <input id="id_prizeForm-TOTAL_FORMS" name="prizeForm-TOTAL_FORMS" type="hidden" value="1"/>
              <input id="id_prizeForm-INITIAL_FORMS" name="prizeForm-INITIAL_FORMS" type="hidden" value="0"/>
              <input id="id_prizeForm-MIN_NUM_FORMS" name="prizeForm-MIN_NUM_FORMS" type="hidden" value="0"/>
              <input id="id_prizeForm-MAX_NUM_FORMS" name="prizeForm-MAX_NUM_FORMS" type="hidden" value="10"/>
            </td>
          </tr>
          </tbody>
        </table>
      </React.Fragment>, document.getElementById('container')
    );
  });

  afterEach(() => {
    ReactDOM.unmountComponentAtNode(document.getElementById('container'));
  });

  it('works', () => {
    subject = render();
  });

  describe('error handling', () => {
    it('does not allow submit if amount is below minimum', () => {
      subject = render();
      TestUtils.Simulate.change(ReactDOM.findDOMNode(subject).querySelector('input[name=amount]'), {target: {value: 4}});
      expectSubmitDisabled('Donation amount below minimum.');
    });

    it('does not allow submit if not all money is allocated', () => {
      subject = render();
      TestUtils.Simulate.change(ReactDOM.findDOMNode(subject).querySelector('input[name=amount]'), {target: {value: 5}});
      TestUtils.Simulate.click(ReactDOM.findDOMNode(subject).querySelector('#show_incentives'));
      expectIncentivesVisible();
      expectSubmitDisabled();
      expect(ReactDOM.findDOMNode(subject).innerText).toContain('You have $5 remaining.');
      TestUtils.Simulate.click(ReactDOM.findDOMNode(subject).querySelector('[data-aid=incentives] [data-aid=result]'));
      TestUtils.Simulate.change(ReactDOM.findDOMNode(subject).querySelector('input[name=new_amount]'), {target: {value: 4}});
      TestUtils.Simulate.click(ReactDOM.findDOMNode(subject).querySelector('#add'));
      expect(ReactDOM.findDOMNode(subject).innerText).toContain('You have $1 remaining.');
      expectSubmitDisabled('Total donation amount not allocated.');
    });

    it('does not allow submit if bid total exceeds donation total', () => {
      subject = render();
      TestUtils.Simulate.change(ReactDOM.findDOMNode(subject).querySelector('input[name=amount]'), {target: {value: 10}});
      TestUtils.Simulate.click(ReactDOM.findDOMNode(subject).querySelector('#show_incentives'));
      expectIncentivesVisible();
      expectSubmitDisabled();
      TestUtils.Simulate.click(ReactDOM.findDOMNode(subject).querySelector('[data-aid=incentives] [data-aid=result]'));
      TestUtils.Simulate.change(ReactDOM.findDOMNode(subject).querySelector('input[name=new_amount]'), {target: {value: 10}});
      TestUtils.Simulate.click(ReactDOM.findDOMNode(subject).querySelector('#add'));
      TestUtils.Simulate.change(ReactDOM.findDOMNode(subject).querySelector('input[name=amount]'), {target: {value: 5}});
      expectSubmitDisabled('Total bid amount cannot exceed donation amount.');
    });

    it('does not allow submit if there are too many incentives present', () => {
      subject = render({
        incentives: [...Array(11).keys()].map(i => (
          {
            id: i,
            name: `Challenge #${i}`,
            goal: '1000.00',
            runname: 'Test Run',
            amount: '0.00',
            count: 0,
            description: `Description #${i}`
          }
        ))
      });
      TestUtils.Simulate.change(ReactDOM.findDOMNode(subject).querySelector('input[name=amount]'), {target: {value: 11}});
      TestUtils.Simulate.click(ReactDOM.findDOMNode(subject).querySelector('#show_incentives'));
      expectIncentivesVisible();
      expectSubmitDisabled();
      [...Array(11).keys()].forEach(i => {
        TestUtils.Simulate.click(ReactDOM.findDOMNode(subject).querySelectorAll('[data-aid=incentives] [data-aid=result]')[i]);
        TestUtils.Simulate.change(ReactDOM.findDOMNode(subject).querySelector('input[name=new_amount]'), {target: {value: 1}});
        TestUtils.Simulate.click(ReactDOM.findDOMNode(subject).querySelector('#add'));
      });
      expectSubmitDisabled('Too many incentives.');
    });

    it('does not allow submit if an expired incentive is present', () => {
      subject = render({
        initialIncentives: [{
          bid: null,
          amount: '5.00',
          customoptionname: '',
        }],
        formErrors: {
          bidsform: [
            {bid: 'Bid does not exist or is closed.'},
          ],
          commentform: {}
        },
        initialForm: {
          amount: '5.00',
        },
      });
      expectSubmitDisabled('At least one incentive is no longer valid.');
    });
  });

  describe('happy paths', () => {
    it('valid amount only', () => {
      subject = render();
      TestUtils.Simulate.change(ReactDOM.findDOMNode(subject).querySelector('input[name=amount]'), {target: {value: 5}});
      TestUtils.Simulate.submit(ReactDOM.findDOMNode(subject));
      expect([...formData.entries()].sort((a, b) => a[0].localeCompare(b[0]))).toEqual([
          ['amount', '5'],
          ['bidsform-INITIAL_FORMS', '0'],
          ['bidsform-MAX_NUM_FORMS', '10'],
          ['bidsform-MIN_NUM_FORMS', '0'],
          ['bidsform-TOTAL_FORMS', '0'],
          ['comment', ''],
          ['csrfmiddlewaretoken', 'deadbeef'],
          ['prizeForm-INITIAL_FORMS', '0'],
          ['prizeForm-MAX_NUM_FORMS', '10'],
          ['prizeForm-MIN_NUM_FORMS', '0'],
          ['prizeForm-TOTAL_FORMS', '1'],
          ['requestedalias', ''],
          ['requestedemail', ''],
          ['requestedsolicitemail', 'CURR'],
          ['requestedvisibility', 'ANON'],
        ]
      );
    });

    it('all fields filled in', () => {
      subject = render();
      TestUtils.Simulate.change(ReactDOM.findDOMNode(subject).querySelector('input[name=amount]'), {target: {value: 5}});
      TestUtils.Simulate.change(ReactDOM.findDOMNode(subject).querySelector('input[name=requestedalias]'), {target: {value: 'skavenger'}});
      TestUtils.Simulate.change(ReactDOM.findDOMNode(subject).querySelector('input[name=requestedemail]'), {target: {value: 'nobody@example.com'}});
      TestUtils.Simulate.change(ReactDOM.findDOMNode(subject).querySelector('textarea[name=comment]'), {target: {value: 'Greetings from Germany!'}});
      TestUtils.Simulate.submit(ReactDOM.findDOMNode(subject));
      expect([...formData.entries()].sort((a, b) => a[0].localeCompare(b[0]))).toEqual([
          ['amount', '5'],
          ['bidsform-INITIAL_FORMS', '0'],
          ['bidsform-MAX_NUM_FORMS', '10'],
          ['bidsform-MIN_NUM_FORMS', '0'],
          ['bidsform-TOTAL_FORMS', '0'],
          ['comment', 'Greetings from Germany!'],
          ['csrfmiddlewaretoken', 'deadbeef'],
          ['prizeForm-INITIAL_FORMS', '0'],
          ['prizeForm-MAX_NUM_FORMS', '10'],
          ['prizeForm-MIN_NUM_FORMS', '0'],
          ['prizeForm-TOTAL_FORMS', '1'],
          ['requestedalias', 'skavenger'],
          ['requestedemail', 'nobody@example.com'],
          ['requestedsolicitemail', 'CURR'],
          ['requestedvisibility', 'ALIAS'],
        ]
      );
    });

    it('email opt in', () => {
      subject = render();
      TestUtils.Simulate.change(ReactDOM.findDOMNode(subject).querySelector('input[name=amount]'), {target: {value: 5}});
      TestUtils.Simulate.click(ReactDOM.findDOMNode(subject).querySelector('#email_optin'));
      TestUtils.Simulate.submit(ReactDOM.findDOMNode(subject));
      expect(formData.get('requestedsolicitemail')).toBe('OPTIN');
    });

    it('email opt out', () => {
      subject = render();
      TestUtils.Simulate.change(ReactDOM.findDOMNode(subject).querySelector('input[name=amount]'), {target: {value: 5}});
      TestUtils.Simulate.click(ReactDOM.findDOMNode(subject).querySelector('#email_optout'));
      TestUtils.Simulate.submit(ReactDOM.findDOMNode(subject));
      expect(formData.get('requestedsolicitemail')).toBe('OPTOUT');
    });

    it('incentives', () => {
      subject = render();
      const node = ReactDOM.findDOMNode(subject);
      TestUtils.Simulate.change(node.querySelector('input[name=amount]'), {target: {value: 15}});
      TestUtils.Simulate.click(node.querySelector('#show_incentives'));
      expectIncentivesVisible();
      TestUtils.Simulate.click(node.querySelectorAll('[data-aid=incentives] [data-aid=result]')[0]);
      TestUtils.Simulate.change(node.querySelector('input[name=new_amount]'), {target: {value: 5}});
      TestUtils.Simulate.click(node.querySelector('#add'));
      TestUtils.Simulate.click(node.querySelectorAll('[data-aid=incentives] [data-aid=result]')[1]);
      TestUtils.Simulate.change(node.querySelectorAll('[data-aid=incentives] input[type=checkbox]')[1], {target: {checked: true}});
      TestUtils.Simulate.change(node.querySelector('input[name=new_amount]'), {target: {value: 5}});
      TestUtils.Simulate.click(node.querySelector('#add'));
      TestUtils.Simulate.click(node.querySelectorAll('[data-aid=incentives] [data-aid=result]')[1]);
      TestUtils.Simulate.change(node.querySelectorAll('[data-aid=incentives] input[type=checkbox]')[0], {target: {checked: true}});
      TestUtils.Simulate.change(node.querySelector('[data-aid=incentives] input[name=newOptionValue]'), {target: {value: 'Black'}});
      TestUtils.Simulate.change(node.querySelector('input[name=new_amount]'), {target: {value: 5}});
      TestUtils.Simulate.click(node.querySelector('#add'));
      TestUtils.Simulate.submit(node);
      expect([...formData.entries()].sort((a, b) => a[0].localeCompare(b[0]))).toEqual([
          ['amount', '15'],
          ['bidsform-0-amount', '5'],
          ['bidsform-0-bid', '1'],
          ['bidsform-0-customoptionname', ''],
          ['bidsform-1-amount', '5'],
          ['bidsform-1-bid', '3'],
          ['bidsform-1-customoptionname', ''],
          ['bidsform-2-amount', '5'],
          ['bidsform-2-bid', '2'],
          ['bidsform-2-customoptionname', 'Black'],
          ['bidsform-INITIAL_FORMS', '0'],
          ['bidsform-MAX_NUM_FORMS', '10'],
          ['bidsform-MIN_NUM_FORMS', '0'],
          ['bidsform-TOTAL_FORMS', '3'],
          ['comment', ''],
          ['csrfmiddlewaretoken', 'deadbeef'],
          ['prizeForm-INITIAL_FORMS', '0'],
          ['prizeForm-MAX_NUM_FORMS', '10'],
          ['prizeForm-MIN_NUM_FORMS', '0'],
          ['prizeForm-TOTAL_FORMS', '1'],
          ['requestedalias', ''],
          ['requestedemail', ''],
          ['requestedsolicitemail', 'CURR'],
          ['requestedvisibility', 'ANON'],
      ]);
    });
  });

  function expectIncentivesVisible() {
    expect(ReactDOM.findDOMNode(subject).querySelector('#show_incentives').disabled).toBe(true);
  }

  function expectSubmitDisabled(message) {
    expect(ReactDOM.findDOMNode(subject).querySelector('#skip_incentives').disabled).toBe(true, 'skip was not disabled');
    const finish = ReactDOM.findDOMNode(subject).querySelector('#finish');
    if (finish === null) {
      expect(finish).toBe(null);
    } else {
      expect(finish.disabled).toBe(true, 'finish was not disabled');
    }
    if (message) {
      expect(ReactDOM.findDOMNode(subject).querySelector('.error').innerText).toContain(message);
    }
  }

  function render(props = {}) {
    const defaultProps = {
      csrfToken: 'deadbeef',
      incentives: [
        {
          id: 1,
          goal: '1000.00',
          amount: '0.00',
          count: 0,
          name: 'Challenge',
          runname: 'Test Run',
          description: 'It is difficult but entertaining.',
        },
        {
          id: 2,
          amount: '0.00',
          count: 0,
          custom: true,
          description: 'Which color?',
          name: 'Paint Color',
          runname: 'Test Run',
        },
        {
          id: 3,
          amount: '0.00',
          count: 0,
          name: 'Red',
          runname: 'Test Run',
          description: '',
          parent: {
            id: 2,
            custom: true,
            description: 'Which color?',
            name: 'Paint Color',
          },
        },
        {
          id: 4,
          amount: '0.00',
          count: 0,
          name: 'Blue',
          runname: 'Test Run',
          description: '',
          parent: {
            id: 2,
            custom: true,
            description: 'Which color?',
            name: 'Paint Color',
          },
        },
      ],
      initialForm: {},
      initialIncentives: [],
      formErrors: {
        bidsform: [],
        commentform: {},
      },
      event: {
        receivername: 'My Pizza Fund',
      },
      donateUrl: '/donate/',
      prizes: [],
      prizesUrl: '/prizes/',
      onSubmit: e => {
        formData = new FormData(e.target);
      },
    };

    return TestUtils.renderIntoDocument(
      <React.Fragment>
        <Donate
          {...defaultProps}
          {...props}
        />
      </React.Fragment>
    );
  }
});