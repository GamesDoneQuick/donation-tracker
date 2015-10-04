import React, { Component } from 'react';
import HTML5Backend from 'react-dnd/modules/backends/HTML5';
import { DragDropContext } from 'react-dnd/modules';
import { Link, RouteHandler } from 'react-router';
import { connect } from 'react-redux';
import _ from 'underscore';
import Spinner from '../public/spinner';
import Dropdown from '../public/dropdown';
import { actions, store } from '../public/api';

class App extends Component {
    render() {
        const { events, status, dropdowns, toggleDropdown } = this.props;
        return (
            <div style={{position: 'relative'}} style={{width: '1600px', overflow: 'scroll'}}>
                <Link to={window.ROOT_PATH + "schedule_editor"}>Schedule Editor</Link>
                <Spinner spinning={status.event === 'loading'}>
                    <Dropdown open={dropdowns.app_events} toggle={toggleDropdown.bind(null, 'app_events')}>
                        <div style={{border: '1px solid', position: 'absolute', left: '0px', top: '30px', backgroundColor: 'white', minWidth: '200px', maxHeight: '120px', overflowY: 'auto' }}>
                            <ul style={{display: 'block'}}>
                                {events ? events.map((e) => {
                                    return (
                                        <li key={e.pk}>
                                            <Link to={window.ROOT_PATH + 'schedule_editor/:event'} params={{event: e.pk}}>{e.short}</Link>
                                        </li>
                                    );
                                })
                                    : null
                                }
                            </ul>
                        </div>
                    </Dropdown>
                </Spinner>
                <RouteHandler />
            </div>
        );
    }

    componentWillMount() {
        this.props.loadModels('event');
    }
}

function select(state) {
    //console.log('select', JSON.stringify(state));
    const { models, saving, status, dropdowns } = state;
    const { events } = models;
    return {
        events,
        saving,
        status,
        dropdowns,
    };
}

function dispatch(dispatch) {
    return {
        loadModels: (model, params, compare, additive) => {
            dispatch(actions.models.loadModels(model, params, compare, additive));
        },
        saveModels: (models) => {
            dispatch(actions.models.saveModels(models));
        },
        toggleDropdown: (dropdown) => {
            dispatch(actions.dropdowns.toggleDropdown(dropdown));
        },
    };
}

App = DragDropContext(HTML5Backend)(connect(select, dispatch)(App, {store: store}));
App.store = store;

module.exports = App;
