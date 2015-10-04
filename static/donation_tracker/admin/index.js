import React from 'react';
import ReactRouter, { Route, HistoryLocation } from 'react-router';
import jQuery from 'jquery';
import App from './app';
import ScheduleEditor from './schedule_editor';
import { Provider } from 'react-redux';
import { DevTools, DebugPanel, LogMonitor } from 'redux-devtools/lib/react';

let $ = jQuery;

$(window).load(() => {
    ReactRouter.run(
        <Route handler={App} path={window.ROOT_PATH}>
            <Route name="schedule_editor" handler={ScheduleEditor}>
                <Route path=":event" handler={ScheduleEditor}/>
            </Route>
        </Route>,
        HistoryLocation,
        (Handler, routerState) => {
            React.render(
                <span>
                    <Provider store={App.store}>
                        {() => <Handler routerState={routerState} />}
                    </Provider>
                    { __DEVTOOLS__ ?
                        <DebugPanel top right bottom>
                            <DevTools store={App.store} monitor={LogMonitor} />
                        </DebugPanel>
                    : null}
                </span>
                ,
                document.getElementById("container"));
        });
});
