import $ from 'jquery';
import React from 'react';
import ReactDOM from 'react-dom';
import { Router, Route, browserHistory, IndexRoute } from 'react-router';
import { Provider } from 'react-redux';
import { syncHistoryWithStore } from 'react-router-redux';

import App from './app';
import ScheduleEditor from './schedule_editor';
import ajaxSetup from '../public/ajaxsetup';
import DevTools from '../devtools';

if (__DEVTOOLS__) {
    window.store = App.store;
}

const history = syncHistoryWithStore(browserHistory, App.store);

$(window).load(() => {
    ajaxSetup($);

    ReactDOM.render(
        <Provider store={App.store}>
            <span>
                <Router history={history}>
                    <Route path={window.ROOT_PATH} component={App}>
                        <Route path="schedule_editor" component={ScheduleEditor}>
                            <Route path=":event" component={ScheduleEditor}/>
                        </Route>
                    </Route>
                </Router>
                { __DEVTOOLS__ ? <DevTools /> : null}
            </span>
        </Provider>,
        document.getElementById("container"));
});
