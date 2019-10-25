import React from 'react';
import {Route} from 'react-router';
import {Link} from 'react-router-dom';
import {connect, useDispatch, useSelector} from 'react-redux';
import Spinner from '../public/spinner';
import Dropdown from '../public/dropdown';
import {actions, store, history} from '../public/api';
import ScheduleEditor from "./schedule_editor";

const App = (props) => {
  const {match} = props;
  const dispatch = useDispatch();

  const {events, saving, status, singletons} = useSelector((state) => ({
    events: state.models.event,
    saving: state.saving,
    status: state.status,
    singletons: state.singletons,
  }));

  React.useEffect(() => {
    dispatch(actions.singletons.fetchMe());
  }, []);

  React.useEffect(() => {
    if (status.event !== 'success' && status.event !== 'loading') {
      dispatch(actions.models.loadModels('event'));
    }
  }, [dispatch, status.event]);

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

App.store = store;
App.history = history;

export default App;
