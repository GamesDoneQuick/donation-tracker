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
  drafts,
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
    id =>
      saveField(
        speedruns.find(sr => sr.id === id),
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
        {speedruns.map(speedrun => {
          const { id } = speedrun;
          const draft = drafts[id];
          const error = draft && draft._error;
          const fieldErrors = draft && draft._fields && draft._fields.__all__;
          return (
            <React.Fragment key={id}>
              {error ? (
                <>
                  {error !== 'Validation Error' ? (
                    <tr key={`error-${id}`}>
                      <td colSpan="10">
                        <ErrorList errors={[error]} />
                      </td>
                    </tr>
                  ) : null}
                  {fieldErrors ? (
                    <tr key={`error-${id}-__all__`}>
                      <td colSpan="10">
                        <ErrorList errors={fieldErrors} />
                      </td>
                    </tr>
                  ) : null}
                </>
              ) : null}
              <Speedrun
                key={id}
                speedrun={speedrun}
                draft={draft}
                moveSpeedrun={moveSpeedrun}
                saveField={saveField}
                editModel={null}
                cancelEdit={cancelEdit}
                saveModel={saveModel}
                updateField={updateField}
              />
            </React.Fragment>
          );
        })}
        {Object.keys(drafts).map(id => {
          if (id >= 0) {
            return null;
          }
          const draft = drafts[id];
          return (
            <React.Fragment key={id}>
              {draft && draft._error ? (
                <>
                  {draft._error !== 'Validation Error' ? (
                    <tr key={`error-${id}`}>
                      <td colSpan="10">{draft._error}</td>
                    </tr>
                  ) : null}
                  {((draft._fields && draft._fields.__all__) || []).map((error, i) => (
                    <tr key={`error-${id}-__all__-${i}`}>
                      <td colSpan="10">{error}</td>
                    </tr>
                  ))}
                </>
              ) : null}
              <Speedrun
                key={id}
                speedrun={draft}
                draft={draft}
                cancelEdit={cancelEdit}
                saveModel={saveModel}
                updateField={updateField}
              />
            </React.Fragment>
          );
        })}
      </tbody>
    </table>
  );
}

SpeedrunTable.propTypes = {
  // TODO: no `object`
  cancelEdit: PropTypes.func.isRequired,
  editModel: PropTypes.func.isRequired,
  drafts: PropTypes.object.isRequired,
  event: PropTypes.object.isRequired,
};

export default SpeedrunTable;
