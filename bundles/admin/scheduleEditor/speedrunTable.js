import React, { useCallback } from 'react';
import PropTypes from 'prop-types';

import ErrorList from '@public/errorList';

import EmptyTableDropTarget from './dragDrop/emptyTableDropTarget';
import Speedrun from './speedrun.js';

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

function Header({ title }) {
  return (
    <thead>
      <tr>
        <td colSpan="10" style={{ textAlign: 'center' }}>
          {title}
        </td>
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

Header.propTypes = {
  title: PropTypes.node,
};

function SpeedrunTable({
  cancelEdit,
  editModel,
  event,
  moveSpeedrun,
  saveField,
  saveModel,
  speedruns = [],
  updateField,
}) {
  speedruns = [...(speedruns || [])].sort(orderSort);

  const localMoveSpeedrun = useCallback(
    pk =>
      saveField(
        speedruns.find(sr => sr.pk === pk),
        'order',
        1,
      ),
    [saveField, speedruns],
  );

  // this is hard as hell to understand and kinda slow so uh maybe clean it up a bit
  return (
    <table className="table table-striped table-condensed small">
      <Header title={event ? event.name : 'All Events'} />
      <tbody>
        {speedruns[0] && speedruns[0].order === null ? (
          <EmptyTableDropTarget elementType="tr" moveSpeedrun={localMoveSpeedrun}>
            <td style={{ textAlign: 'center' }} colSpan="10">
              Drop a run here to start the schedule
            </td>
          </EmptyTableDropTarget>
        ) : null}
        {speedruns.map(speedrun => (
          <Speedrun
            key={speedrun.pk}
            speedrun={speedrun}
            moveSpeedrun={moveSpeedrun}
            saveField={saveField}
            editModel={editModel}
            cancelEdit={cancelEdit}
            saveModel={saveModel}
            updateField={updateField}
          />
        ))}
      </tbody>
    </table>
  );
}

SpeedrunTable.propTypes = {
  // TODO: no `object`
  cancelEdit: PropTypes.func.isRequired,
  editModel: PropTypes.func.isRequired,
  event: PropTypes.object.isRequired,
};

export default SpeedrunTable;
