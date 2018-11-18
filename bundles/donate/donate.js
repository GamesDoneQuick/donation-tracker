import React from 'react';
import PropTypes from 'prop-types';
import _ from 'lodash';
import cn from 'classnames';

import styles from './donate.css';

const IncentiveProps = PropTypes.shape({
  id: PropTypes.number.isRequired,
  parent: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    custom: PropTypes.bool.isRequired,
    description: PropTypes.string.isRequired,
  }),
  name: PropTypes.string.isRequired,
  runname: PropTypes.string.isRequired,
  amount: PropTypes.string.isRequired, // TODO: this and goal should be numbers but django seems to be serializing them as strings?
  count: PropTypes.number.isRequired,
  goal: PropTypes.string,
  description: PropTypes.string.isRequired,
});

class Incentives extends React.PureComponent {
  static propTypes = {
    step: PropTypes.number.isRequired,
    total: PropTypes.number.isRequired,
    incentives: PropTypes.arrayOf(IncentiveProps.isRequired).isRequired,
    addIncentive: PropTypes.func.isRequired,
  };

  static defaultProps = {
    step: 0.01,
  };

  state = {
    search: '',
    amount: 0,
    bidsformempty: [],
  };

  static getDerivedStateFromProps(props, state) {
    const addedState = {};
    if (state.selectedChoice) {
      addedState.newOption = false;
      addedState.newOptionValue = '';
    }
    if (state.newOption) {
      addedState.newOption = state.newOption;
      addedState.selectedChoice = null;
    } else {
      addedState.newOptionValue = '';
    }

    return addedState;
  }

  componentDidMount() {
    this.setState({bidsformempty: Array.from(document.querySelector('table[data-form=bidsform][data-form-type=empty]').querySelectorAll('input')).filter(i => i.id)});
  }

  matchResults_() {
    const search = this.state.search.toLowerCase();
    let {incentives} = this.props;
    if (search) {
      incentives = incentives.filter(i => {
        return (i.parent ? i.parent.name : i.name).toLowerCase().includes(search)
          || (i.runname && i.runname.toLowerCase().includes(search));
      });
    }
    incentives = incentives.map(i => ({
      id: i.id,
      run: i.runname,
      name: i.parent ? i.parent.name : i.name
    }));
    return _.uniqBy(incentives, i => `${i.run}--${i.name}`);
  }

  addIncentiveDisabled_() {
    if (this.state.amount <= 0) {
      return 'Amount must be greater than 0.';
    } else if (this.state.amount > this.props.total) {
      return `Amount cannot be greater than $${this.props.total}.`;
    } else if (this.state.selected && !+this.state.selected.goal) {
      if (this.state.newOption && !this.state.newOptionValue) {
        return 'Must enter new option.';
      } else if (!this.state.newOption && !this.state.selectedChoice) {
        return 'Must pick an option.';
      }
    }
    return null;
  }

  addIncentive = (e) => {
    e.preventDefault();
    this.props.addIncentive({
      bid: (this.state.newOptionValue || !this.state.selectedChoice) ? this.state.selected.id : this.state.selectedChoice,
      amount: (+this.state.amount),
      customoptionname: this.state.newOptionValue,
    });
    this.setState({selected: null});
  };

  setChecked = key => {
    return e => {
      this.setState({[key]: e.target.checked});
    };
  };

  setValue = key => {
    return e => {
      this.setState({[key]: e.target.value});
    }
  };

  select = id => {
    return () => {
      const {
        total,
        incentives,
      } = this.props;
      if (total === 0) {
        return;
      }
      const result = incentives.find(i => i.id === id);
      this.setState({
        selected: {...(result.parent || result), runname: result.runname},
        choices: result.parent ? incentives.filter(i => i.parent && i.parent.id === result.parent.id) : incentives.filter(i => i.parent && i.parent.id === result.id),
        newOption: false,
        newOptionValue: '',
        selectedChoice: null,
        amount: total,
      });
    };
  };

  render() {
    const {
      amount,
      bidsformempty,
      choices,
      search,
      selected,
      newOption,
      newOptionValue,
      selectedChoice,
    } = this.state;
    const {
      step,
      total,
      currentIncentives,
      errors,
      incentives,
      deleteIncentive,
    } = this.props;
    const addIncentiveDisabled = this.addIncentiveDisabled_();
    return (
      <div className={styles['incentives']} data-aid='incentives'>
        <div className={styles['left']}>
          <div className={styles['searches']}>
            <input className={styles['search']} value={search} onChange={this.setValue('search')}
                   placeholder='Filter Results'/>
            <div className={styles['results']}>
              {
                this.matchResults_().map(result =>
                  <div className={styles['result']} data-aid='result' key={result.id} onClick={this.select(result.id)}>
                    <div className={styles['resultRun']}>{result.run}</div>
                    <div className={styles['resultName']}>{result.name}</div>
                  </div>
                )
              }
            </div>
          </div>
          <div className={styles['assigned']}>
            <div className={styles['header']}>YOUR INCENTIVES</div>
            {currentIncentives.map((ci, k) => {
                const incentive = incentives.find(i => i.id === ci.bid) || {name: errors[k].bid, id: `error-${k}`};
                return (
                  <div key={incentive.id} onClick={deleteIncentive(k)} className={styles['item']}>
                    {bidsformempty && bidsformempty.map(i =>
                      <input
                        key={i.name.replace('__prefix__', k)}
                        id={i.id.replace('__prefix__', k)}
                        name={i.name.replace('__prefix__', k)}
                        type='hidden'
                        value={ci[i.name.split('-').slice(-1)[0]] || ''}
                      />
                    )}
                    <div className={cn(styles['runname'], styles['cubano'])}>{incentive.runname}</div>
                    <div>{incentive.parent ? incentive.parent.name : incentive.name}</div>
                    <div>Choice: {ci.customoptionname || incentive.name}</div>
                    <div>Amount: ${ci.amount}</div>
                    <button className={cn(styles['delete'], styles['cubano'])} type='button'>DELETE</button>
                  </div>
                );
              }
            )}

          </div>
        </div>
        {selected ?
          <div className={styles['right']}>
            <div className={cn(styles['runname'], styles['cubano'])}>{selected.runname}</div>
            <div className={styles['name']}>{selected.name}</div>
            <div className={styles['description']}>{selected.description}</div>
            {(+selected.goal) ?
              <div className={styles['goal']}>
                <div>Current Raised Amount:</div>
                <div>${selected.amount} / ${selected.goal}</div>
              </div> :
              null}
            {selected.custom ?
              <React.Fragment>
                <div>
                  <input type='checkbox' checked={newOption} onChange={this.setChecked('newOption')} name='custom'/>
                  <label htmlFor='custom'>Nominate a new option!</label>
                </div>
                <div>
                  <input className={styles['underline']} value={newOptionValue} disabled={!newOption} type='text'
                         name='newOptionValue'
                         onChange={this.setValue('newOptionValue')} placeholder='Enter Here'/>
                </div>
              </React.Fragment> :
              null}
            {choices.length ?
              <React.Fragment>
                <div>Choose an existing option:</div>
                {choices.map(choice =>
                  (<div key={choice.id} className={styles['choice']}>
                    <input checked={selectedChoice === choice.id} type='checkbox'
                           onChange={() => this.setState({selectedChoice: choice.id, newOption: false})}
                           name={`choice-${choice.id}`}/>
                    <label htmlFor={`choice-${choice.id}`}>{choice.name}</label>
                    <span>${choice.amount}</span>
                  </div>)
                )}
              </React.Fragment> :
              null}
            <div className={styles['amountCTA']}>Amount to put towards incentive:</div>
            <div className={styles['amount']}>
              <input className={styles['underline']} value={amount} name='new_amount' type='number' step={step} min={0}
                     max={total}
                     onChange={this.setValue('amount')} placeholder='Enter Here'/>
              <label htmlFor='new_amount'>You have ${total} remaining.</label>
            </div>
            <div>
              <button className={cn(styles['add'], styles['inverse'])} id='add' disabled={addIncentiveDisabled}
                      onClick={this.addIncentive}>ADD
              </button>
              {addIncentiveDisabled && <label htmlFor='add' className='error'>{addIncentiveDisabled}</label>}
            </div>
          </div> :
          <div className={styles['right']}>You have ${total} remaining.</div>}
      </div>
    );
  }
}

class Donate extends React.PureComponent {
  static propTypes = {
    incentives: PropTypes.arrayOf(IncentiveProps.isRequired).isRequired,
    formErrors: PropTypes.shape({
      bidsform: PropTypes.array.isRequired,
      commentform: PropTypes.object.isRequired,
    }).isRequired,
    initialForm: PropTypes.shape({
      requestedalias: PropTypes.string,
      requestedemail: PropTypes.string,
      amount: PropTypes.string,
    }).isRequired,
    initialIncentives: PropTypes.arrayOf(PropTypes.shape({
      bid: PropTypes.number, // will be null if the bid closed while we were filling it out
      amount: PropTypes.string.isRequired,
      customoptionname: PropTypes.string.isRequired,
    }).isRequired).isRequired,
    event: PropTypes.shape({
      receivername: PropTypes.string.isRequired,
    }).isRequired,
    step: PropTypes.number.isRequired,
    minimumDonation: PropTypes.number.isRequired,
    maximumDonation: PropTypes.number.isRequired,
    donateUrl: PropTypes.string.isRequired,
    prizes: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.number.isRequired,
      description: PropTypes.string,
      minimumbid: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
    }).isRequired).isRequired,
    prizesUrl: PropTypes.string.isRequired,
    rulesUrl: PropTypes.string,
    csrfToken: PropTypes.string,
    onSubmit: PropTypes.func,
  };

  static defaultProps = {
    step: 0.01,
    minimumDonation: 5,
    maximumDonation: 10000,
    initialIncentives: [],
  };

  state = {
    showIncentives: this.props.initialIncentives.length !== 0,
    currentIncentives: this.props.initialIncentives || [],
    requestedalias: this.props.initialForm.requestedalias || '',
    requestedemail: this.props.initialForm.requestedemail || '',
    requestedsolicitemail: this.props.initialForm.requestedsolicitemail || 'CURR',
    comment: this.props.initialForm.comment || '',
    amount: this.props.initialForm.amount || '',
    bidsformmanagement: null,
    prizesform: null,
  };

  setValue = key => {
    return e => {
      this.setState({[key]: e.target.value});
    }
  };

  setAmount = (amount) => {
    return e => {
      this.setState({amount});
      e.preventDefault();
    }
  };

  setEmail = (requestedsolicitemail) => {
    return e => {
      this.setState({requestedsolicitemail});
      e.preventDefault();
    }
  };

  addIncentive_ = (incentive) => {
    const {
      currentIncentives,
    } = this.state;
    const existing = currentIncentives.findIndex(ci => ci.bid === incentive.bid);
    let newIncentives;
    if (existing !== -1) {
      incentive.amount += (+currentIncentives[existing].amount);
      newIncentives = currentIncentives.slice(0, existing).concat([incentive]).concat(currentIncentives.slice(existing + 1));
    } else {
      newIncentives = currentIncentives.concat([incentive]);
    }
    this.setState({currentIncentives: newIncentives});
  };

  deleteIncentive_ = (i) => {
    return e => {
      const {
        currentIncentives,
      } = this.state;
      this.setState({currentIncentives: currentIncentives.slice(0, i).concat(currentIncentives.slice(i + 1))});
    }
  };

  sumIncentives_() {
    return this.state.currentIncentives.reduce((sum, ci) => sum + (+ci.amount), 0);
  }

  finishDisabled_() {
    const {
      amount,
      currentIncentives,
      showIncentives,
    } = this.state;
    const {
      minimumDonation,
      incentives,
    } = this.props;
    if (this.sumIncentives_() > amount) {
      return 'Total bid amount cannot exceed donation amount.';
    }
    if (showIncentives && this.sumIncentives_() < amount) {
      return 'Total donation amount not allocated.';
    }
    if (amount < minimumDonation) {
      return 'Donation amount below minimum.';
    }
    if (currentIncentives.some(ci => !incentives.find(i => i.id === ci.bid))) {
      return 'At least one incentive is no longer valid.';
    }
    if (currentIncentives.length > 10) {
      return 'Too many incentives.';
    }
    return null;
  }

  wrapPrize_(prize, children) {
    return prize.url ? <a href={prize.url}>{children}</a> : children;
  }

  componentDidMount() {
    this.setState({
      bidsformmanagement: Array.from(document.querySelector('table[data-form=bidsform][data-form-type=management]').querySelectorAll('input')).filter(i => i.id),
      prizesform: Array.from(document.querySelector('table[data-form=prizesform]').querySelectorAll('input')).filter(i => i.id),
    });
  }

  render() {
    const {
      showIncentives,
      currentIncentives,
      requestedalias,
      requestedemail,
      requestedsolicitemail,
      comment,
      amount,
      bidsformmanagement,
      prizesform,
    } = this.state;
    const {
      step,
      event,
      prizesUrl,
      rulesUrl,
      minimumDonation,
      maximumDonation,
      formErrors,
      prizes,
      donateUrl,
      incentives,
      csrfToken,
      onSubmit,
    } = this.props;
    // TODO: show more form errors
    const finishDisabled = this.finishDisabled_();
    return (
      <form className={styles['donationForm']} action={donateUrl} method='post' onSubmit={onSubmit}>
        <input type='hidden' name='csrfmiddlewaretoken' value={csrfToken}/>
        <div className={styles['donation']}>
          <div className={cn(styles['cubano'], styles['thankyou'])}>THANK YOU</div>
          <div className={cn(styles['cubano'], styles['fordonation'])}>FOR YOUR DONATION</div>
          <div className={styles['hundred']}>100% of your donation goes directly to {event.receivername}.</div>
          <div className={styles['biginput']}>
            <input type='hidden' name='requestedvisibility' value={requestedalias ? 'ALIAS' : 'ANON'}/>
            <input className={cn(styles['underline'], styles['preferredNameInput'])} placeholder='Preferred Name/Alias'
                   type='text' name='requestedalias' value={requestedalias} onChange={this.setValue('requestedalias')}
                   maxLength='32'/>
            <div>(Leave blank for Anonymous)</div>
          </div>
          <div className={styles['biginput']}>
            <input className={cn(styles['underline'], styles['preferredEmailInput'])} placeholder='Email Address'
                   type='email' name='requestedemail' value={requestedemail} maxLength='128'
                   onChange={this.setValue('requestedemail')}/>
            <div>(Click <a className={cn('block-external', styles['privacy'])}
                           href='https://gamesdonequick.com/privacy/' target='_blank'
                           rel='noopener noreferrer'>here</a> for our privacy policy)
            </div>
          </div>
          <div className={styles['emailCTA']}>
            Do you want to receive emails from {event.receivername}?
          </div>
          <div className={styles['emailButtons']}>
            <input type='hidden' name='requestedsolicitemail' value={requestedsolicitemail}/>
            <button id='email_optin' className={cn({[styles['selected']]: requestedsolicitemail === 'OPTIN'})}
                    disabled={requestedsolicitemail === 'OPTIN'} onClick={this.setEmail('OPTIN')}>Yes
            </button>
            <button id='email_optout' className={cn({[styles['selected']]: requestedsolicitemail === 'OPTOUT'})}
                    disabled={requestedsolicitemail === 'OPTOUT'} onClick={this.setEmail('OPTOUT')}>No
            </button>
            <button id='email_curr' className={cn({[styles['selected']]: requestedsolicitemail === 'CURR'})}
                    disabled={requestedsolicitemail === 'CURR'} onClick={this.setEmail('CURR')}>Use Existing Preference
              (No if not already set)
            </button>
          </div>
          <div className={styles['donationArea']}>
            <div className={styles['donationAmount']}>
              <input className={cn(styles['underline'], styles['amountInput'])} placeholder='Enter Amount' type='number'
                     name='amount' value={amount} step={step} min={minimumDonation} max={maximumDonation}
                     onChange={this.setValue('amount')}/>
              <div className={styles['buttons']}>
                <button onClick={this.setAmount(25)}>$25</button>
                <button onClick={this.setAmount(50)}>$50</button>
                <button onClick={this.setAmount(75)}>$75</button>
              </div>
              <div className={styles['buttons']}>
                <button onClick={this.setAmount(100)}>$100</button>
                <button onClick={this.setAmount(250)}>$250</button>
                <button onClick={this.setAmount(500)}>$500</button>
              </div>
              <div>(Minimum donation is ${minimumDonation})</div>
            </div>
            {prizes.length ?
              <div className={styles['prizeInfo']}>
                <div className={styles['cta']}>Donations can enter you to win prizes!</div>
                <div className={styles['prizeList']}>
                  <div className={styles['header']}>CURRENT PRIZE LIST:</div>
                  <div className={styles['prizes']}>
                    {prizes.map(prize =>
                      <div key={prize.id} className={styles['item']}>
                        {this.wrapPrize_(prize,
                          <React.Fragment>
                            <div className={cn(styles['name'], styles['cubano'])}>
                              {prize.name}
                            </div>
                            <div className={styles['bidinfo']}>
                              ${prize.minimumbid} {prize.sumdonations ? 'Total Donations' : 'Minimum Single Donation'}
                            </div>
                          </React.Fragment>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                <div><a className='block-external' href={prizesUrl} target='_blank' rel='noopener noreferrer'>Full
                  prize list (New tab)</a></div>
                {rulesUrl ?
                  <React.Fragment>
                    <div><a className='block-external' href={rulesUrl} target='_blank' rel='noopener noreferrer'>Official
                      Rules (New tab)</a></div>
                    <div className={cn(styles['disclaimer'], styles['cta'])}>No donation necessary for a chance to win.
                      See sweepstakes rules for details and instructions.
                    </div>
                  </React.Fragment> : null}
              </div> :
              null}
          </div>
          <div className={styles['commentArea']}>
            <div className={styles['cubano']}>(OPTIONAL) LEAVE A COMMENT?</div>
            <textarea className={styles['commentInput']} placeholder='Enter Comment Here' value={comment}
                      onChange={this.setValue('comment')} name='comment' maxLength={5000}/>
            <label htmlFor='comment'>Please refrain from offensive language or hurtful remarks. All donation comments
              are screened and will be removed from the website if deemed unacceptable.</label>
          </div>
        </div>
        <div className={styles['incentivesCTA']}>
          <div className={styles['cubano']}>DONATION INCENTIVES</div>
          <div>Donation incentives can be used to add bonus runs to the schedule or influence choices by runners. Do
            you wish to put your donation towards an incentive?
          </div>
          <div className={styles['incentivesButtons']}>
            <button
              className={styles['inverse']}
              disabled={showIncentives}
              id='show_incentives'
              type='button'
              onClick={() => {
                this.setState({showIncentives: true});
              }}>
              YES!
            </button>
            <button
              id='skip_incentives'
              className={styles['inverse']}
              disabled={showIncentives || this.finishDisabled_()}
              type='submit'>
              NO, SKIP INCENTIVES
            </button>
            {!showIncentives && finishDisabled && <label htmlFor='skip' className='error'>{finishDisabled}</label>}
          </div>
        </div>
        {showIncentives ?
          <React.Fragment>
            <Incentives
              step={step}
              errors={formErrors.bidsform}
              incentives={incentives}
              currentIncentives={currentIncentives}
              deleteIncentive={this.deleteIncentive_}
              addIncentive={this.addIncentive_}
              total={(amount || 0) - this.sumIncentives_()}
            />
            <div className={styles['finishArea']}>
              <button
                className={cn(styles['finish'], styles['inverse'], styles['cubano'])}
                id='finish'
                disabled={this.finishDisabled_()}
                type='submit'>
                FINISH
              </button>
              {finishDisabled && <label htmlFor='finish' className='error'>{finishDisabled}</label>}
            </div>
          </React.Fragment> :
          null}
        <React.Fragment>
          {bidsformmanagement && bidsformmanagement.map(i => <input key={i.id} id={i.id} name={i.name}
                                                                    value={i.name.includes('TOTAL_FORMS') ? currentIncentives.length : i.value}
                                                                    type='hidden'/>)}
        </React.Fragment>
        <React.Fragment>
          {prizesform && prizesform.map(i => <input key={i.id} id={i.id} name={i.name} value={i.value} type='hidden'/>)}
        </React.Fragment>
      </form>
    );
  }
};

export default Donate;
