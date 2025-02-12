import React from 'react';
import { connect } from 'react-redux';

import { actions } from '@public/api';
import { hasPermission } from '@public/api/helpers/auth';
import APIErrorList from '@public/APIErrorList';
import { OrderedRun, UnorderedRun } from '@public/apiv2/Models';
import { useEventParam, useMoveRunMutation, useRunsQuery } from '@public/apiv2/reducers/trackerApi';
import Spinner from '@public/spinner';

import SpeedrunTable from './speedrunTable';

class ScheduleEditorOld extends React.Component {
  render() {
    const { speedruns, event, status, moveSpeedrun, editable } = this.props;
    const { saveField_ } = this;
    const loading = status.speedrun === 'loading' || status.event === 'loading' || status.me === 'loading';
    const error = status.speedrun === 'error' || status.event === 'error' || status.me === 'error';
    return (
      <Spinner spinning={loading}>
        {error ? (
          <>
            {status.speedrun === 'error' && <div>Failed to fetch speedruns</div>}
            {status.event === 'error' && <div>Failed to fetch events</div>}
            {status.me === 'error' && <div>Failed to fetch me</div>}
          </>
        ) : (
          <SpeedrunTable
            event={event}
            speedruns={speedruns}
            moveSpeedrun={editable ? moveSpeedrun : null}
            saveField={editable ? saveField_ : null}
          />
        )}
      </Spinner>
    );
  }

  componentDidUpdate(newProps) {
    if (this.props.eventId !== newProps.eventId) {
      this.refreshSpeedruns_(newProps.eventId);
    }
  }

  componentDidMount() {
    this.refreshSpeedruns_(this.props.eventId);
  }

  refreshSpeedruns_(event) {
    const { status } = this.props;
    if (status.event !== 'loading' && status.event !== 'success') {
      this.props.loadModels('event');
    }
    if ((status.speedrun !== 'loading' && status.speedrun !== 'success') || event !== this.props.event) {
      this.props.loadModels('speedrun', { event: event });
    }
  }

  saveField_ = (model, field, value) => {
    this.props.saveField({ type: 'speedrun', ...model }, field, value);
  };
}

function select(state, props) {
  const {
    models: { speedrun: speedruns, event: events },
    status,
    singletons,
  } = state;
  const event = events?.find(e => e.pk === +parseInt(props.eventId)) || null;
  const { me } = singletons;
  return {
    event,
    speedruns,
    status,
    editable:
      me &&
      hasPermission(me, `tracker.change_speedrun`) &&
      (!(event && event.locked) || hasPermission(me, `tracker.can_edit_locked_events`)),
  };
}

function dispatch(dispatch) {
  return {
    loadModels: (model, params, additive) => {
      dispatch(actions.models.loadModels(model, params, additive));
    },
    moveSpeedrun: (source, destination, before) => {
      dispatch(actions.models.setInternalModelField('speedrun', source, 'moving', true));
      if (destination != null) {
        dispatch(actions.models.setInternalModelField('speedrun', destination, 'moving', true));
      }
      dispatch(actions.models.setInternalModelField('speedrun', source, 'errors', null));
      dispatch(
        actions.models.command({
          type: 'MoveSpeedRun',
          params: {
            moving: source,
            other: destination,
            before: before ? 1 : 0,
          },
          fail: json => {
            dispatch(actions.models.setInternalModelField('speedrun', source, 'errors', json.error));
          },
          always: () => {
            dispatch(actions.models.setInternalModelField('speedrun', source, 'moving', false));
            if (destination != null) {
              dispatch(actions.models.setInternalModelField('speedrun', destination, 'moving', false));
            }
          },
        }),
      );
    },
    saveField: (model, field, value) => {
      dispatch(actions.models.saveField(model, field, value));
    },
  };
}

export const Connected = connect(select, dispatch)(ScheduleEditorOld);

export default function ScheduleEditor() {
  const eventId = useEventParam();
  const { data: runs, error, isLoading } = useRunsQuery({ urlParams: eventId, queryParams: { all: '' } });
  const [moveRun, mutation] = useMoveRunMutation();
  const orderedRuns = React.useMemo(
    () => [...(runs || [])].filter((r): r is OrderedRun => r.order != null).sort((a, b) => a.order - b.order),
    [runs],
  );
  const unorderedRuns = React.useMemo(
    () => (runs || []).filter((r): r is UnorderedRun => r.order == null).sort((a, b) => a.name.localeCompare(b.name)),
    [runs],
  );

  return (
    <APIErrorList errors={error}>
      <Spinner spinning={isLoading}>
        {orderedRuns.map(r => {
          return (
            <div key={r.id}>
              {r.name}
              <Spinner spinning={mutation.isLoading && mutation.originalArgs?.id === r.id}>
                <button onClick={() => moveRun({ id: r.id, order: null })}>Remove</button>
              </Spinner>
            </div>
          );
        })}
        {unorderedRuns.map(r => {
          return (
            <div key={r.id}>
              {r.name}{' '}
              <Spinner spinning={mutation.isLoading && mutation.originalArgs?.id === r.id}>
                <button onClick={() => moveRun({ id: r.id, order: 'last' })}>Last</button>
              </Spinner>
            </div>
          );
        })}
      </Spinner>
    </APIErrorList>
  );
}
