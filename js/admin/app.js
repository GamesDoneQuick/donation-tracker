import React, {Component} from 'react';
import PropTypes from 'prop-types';
import HTML5Backend from 'react-dnd-html5-backend';
import {DragDropContext} from 'react-dnd';
import {Route} from 'react-router';
import {Link} from 'react-router-dom';
import {connect} from 'react-redux';
import Spinner from '../public/spinner';
import Dropdown from '../public/dropdown';
import {actions, store, history} from '../public/api';
import ScheduleEditor from "./schedule_editor";

class App extends Component {
  static childContextTypes = {
    STATIC_URL: PropTypes.string,
  };

  getChildContext() {
    return {STATIC_URL: window.STATIC_URL};
  }

  render() {
    const {events, status, match} = this.props;
    return (
      <div style={{position: 'relative'}}>
        <Link to={`${match.url}/schedule_editor`}>Schedule Editor</Link>
        <Spinner spinning={status.event === 'loading'}>
          <Dropdown closeOnClick={true}>
            <div style={{
              border: '1px solid',
              position: 'absolute',
              backgroundColor: 'white',
              minWidth: '200px',
              maxHeight: '120px',
              overflowY: 'auto'
            }}>
              <ul style={{display: 'block'}}>
                {events ? events.map((e) => {
                    return (
                      <li key={e.pk}>
                        <Link to={`${match.url}/schedule_editor/${e.pk}`}>{e.short}</Link>
                      </li>
                    );
                  })
                  : null
                }
              </ul>
            </div>
          </Dropdown>
        </Spinner>
        <Route path={`${match.url}/schedule_editor/:event`} component={ScheduleEditor}/>
      </div>
    );
  }

  componentWillMount() {
    const {
      loadModels,
      status,
      fetchMe,
    } = this.props;
    setTimeout(
      () => {
        if (status.event !== 'success' && status.event !== 'loading') {
          loadModels('event');
        }
      },
      1);
    fetchMe();
  }
}

function select(state) {
  const {saving, status, singletons} = state;
  const {event} = state.models;
  return {
    events: event,
    saving,
    status,
    singletons,
  };
}

function dispatch(dispatch) {
  return {
    fetchMe: () => {
      dispatch(actions.singletons.fetchMe());
    },
    loadModels: (model, params, additive) => {
      dispatch(actions.models.loadModels(model, params, additive));
    },
    saveModels: (models) => {
      dispatch(actions.models.saveModels(models));
    },
  };
}

App = DragDropContext(HTML5Backend)(connect(select, dispatch)(App));
App.store = store;
App.history = history;

export default App;
