import React from 'react';
const { PropTypes } = React;

import SpeedRun from './speedrun.js';
import EmptyTableDropTarget from './drag_drop/empty_table_drop_target';

function orderSort(a, b) {
    if (a.order === null && b.order === null) {
        return 0;
    } else if (a.order !== null && b.order === null) {
        return -1;
    } else if (a.order === null && b.order !== null) {
        return 1;
    } else if (a.order < b.order) {
        return -1;
    } else {
        return 1;
    }
}

class Header extends React.Component {
    render() {
        const { title } = this.props;
        return (
            <thead>
                <tr>
                    <td colSpan="10" style={{textAlign: 'center'}}>{title}</td>
                </tr>
                <tr>
                    <th>Start Time</th>
                    <th>Order</th>
                    <th>Game</th>
                    <th>Runners</th>
                    <th>Console</th>
                    <th>Estimate/Run Time</th>
                    <th>Setup</th>
                    <th>Description</th>
                    <th colSpan="2">Commentators</th>
                </tr>
            </thead>
        );
    }
}

class SpeedRunTable extends React.Component {
    constructor(props) {
        super(props);
        this.newSpeedRun_ = this.newSpeedRun_.bind(this);
    }

    render() {
        const {
            drafts,
            event,
            moveSpeedRun,
            saveField,
            saveModel,
            cancelEdit,
            editModel,
            updateField,
        } = this.props;
        const speedRuns = [...this.props.speedRuns || []].sort(orderSort);
        return (
            <table className="table table-striped table-condensed small">
                <Header title={event ? event.name : 'All Events'} />
                <tbody>
                    {speedRuns[0] && speedRuns[0].order === null ?
                        <EmptyTableDropTarget
                            elementType='tr'
                            moveSpeedRun={(pk) => saveField(speedRuns.find((sr) => sr.pk === pk), 'order', 1)}
                            >
                            <td style={{textAlign: 'center'}} colSpan='10'>
                                Drop a run here to start the schedule
                            </td>
                        </EmptyTableDropTarget>
                        :
                        null
                    }
                    {speedRuns.map((speedRun) => {
                        const { pk } = speedRun;
                        const draft = drafts[pk];
                        return (
                            [
                            (draft && draft._error) ?
                                [
                                    draft._error !== 'Validation Error' ?
                                        <tr key={`error-${pk}`}>
                                            <td colSpan='10'>
                                                {draft._error}
                                            </td>
                                        </tr>
                                        :
                                        null
                                    ,
                                    ...((draft._fields && draft._fields.__all__) || []).map((error, i) =>
                                        <tr key={`error-${pk}-__all__-${i}`}>
                                            <td colSpan='10'>
                                                {error}
                                            </td>
                                        </tr>
                                    )
                                ]
                                :
                                null,
                            <SpeedRun
                                key={pk}
                                speedRun={speedRun}
                                draft={draft}
                                moveSpeedRun={moveSpeedRun}
                                saveField={saveField.bind(null, speedRun)}
                                editModel={editModel.bind(null, speedRun)}
                                cancel={cancelEdit.bind(null, draft)}
                                saveModel={saveModel.bind(null, pk)}
                                updateField={updateField.bind(null, pk)}
                                />
                            ]
                        );
                    })}
                    {Object.keys(drafts).map((pk) => {
                        if (pk >= 0) {
                            return null;
                        }
                        const draft = drafts[pk];
                        return (
                            [
                            (draft && draft._error) ?
                                [
                                    draft._error !== 'Validation Error' ?
                                        <tr key={`error-${pk}`}>
                                            <td colSpan='10'>
                                                {draft._error}
                                            </td>
                                        </tr>
                                        :
                                        null
                                    ,
                                    ...((draft._fields && draft._fields.__all__) || []).map((error, i) =>
                                        <tr key={`error-${pk}-__all__-${i}`}>
                                            <td colSpan='10'>
                                                {error}
                                            </td>
                                        </tr>
                                    )
                                ]
                                :
                                null,
                            <SpeedRun
                                key={pk}
                                draft={draft}
                                cancel={cancelEdit.bind(null, draft)}
                                saveModel={saveModel.bind(null, pk)}
                                updateField={updateField.bind(null, pk)}
                                />
                            ]
                        );
                    })}
                </tbody>
            </table>
        );
    }

    newSpeedRun_() {
        this.props.newSpeedRun();
    }
}

SpeedRunTable.propTypes = {
    // TODO
};

export default SpeedRunTable;
