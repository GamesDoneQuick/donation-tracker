import React from 'react';
import { connect } from 'react-redux';

import { actions } from '@public/api';
import authHelper from '@public/api/helpers/auth';
import Spinner from '@public/spinner';

import SpeedrunTable from './speedrunTable';

class ScheduleEditor extends React.Component {
  render() {
    const { speedruns, event, drafts, status, moveSpeedrun, editable } = this.props;
    const { saveField_, saveModel_, editModel_, cancelEdit_, newSpeedrun_, updateField_ } = this;
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
            drafts={drafts}
            speedruns={speedruns}
            saveModel={editable ? saveModel_ : null}
            editModel={editable ? editModel_ : null}
            cancelEdit={editable ? cancelEdit_ : null}
            newSpeedrun={editable ? newSpeedrun_ : null}
            moveSpeedrun={editable ? moveSpeedrun : null}
            saveField={editable ? saveField_ : null}
            updateField={editable ? updateField_ : null}
          />
        )}
      </Spinner>
    );
  }

  componentDidUpdate(newProps) {
    if (this.props.match.params.event !== newProps.match.params.event) {
      this.refreshSpeedruns_(newProps.match.params.event);
    }
  }

  componentDidMount() {
    this.refreshSpeedruns_(this.props.match.params.event);
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

  saveModel_ = (pk, fields) => {
    this.props.saveDraftModels([{ type: 'speedrun', pk, fields }]);
  };

  editModel_ = model => {
    this.props.newDraftModel({ type: 'speedrun', ...model });
  };

  cancelEdit_ = model => {
    this.props.deleteDraftModel({ type: 'speedrun', ...model });
  };

  newSpeedrun_ = () => {
    this.props.newDraftModel({ type: 'speedrun' });
  };

  updateField_ = (pk, field, value) => {
    this.props.updateDraftModelField('speedrun', pk, field, value);
  };

  saveField_ = (model, field, value) => {
    this.props.saveField({ type: 'speedrun', ...model }, field, value);
  };
}

function select(state, props) {
  const { models, drafts, status, singletons } = state;
  const { speedrun: speedruns, event: events = [] } = models;
  const event = events.find(e => e.pk === parseInt(props.match?.params?.event)) || null;
  const { me } = singletons;
  return {
    event,
    speedruns,
    status,
    drafts: drafts?.speedrun || {},
    editable:
      authHelper.hasPermission(me, `tracker.change_speedrun`) &&
      (!(event && event.locked) || authHelper.hasPermission(me, `tracker.can_edit_locked_events`)),
  };
}

function dispatch(dispatch) {
  return {
    loadModels: (model, params, additive) => {
      dispatch(actions.models.loadModels(model, params, additive));
    },
    moveSpeedrun: (source, destination, before) => {
      dispatch(actions.models.setInternalModelField('speedrun', source, 'moving', true));
      dispatch(actions.models.setInternalModelField('speedrun', destination, 'moving', true));
      dispatch(
        actions.models.command({
          type: 'MoveSpeedRun',
          params: {
            moving: source,
            other: destination,
            before: before ? 1 : 0,
          },
          always: () => {
            dispatch(actions.models.setInternalModelField('speedrun', source, 'moving', false));
            dispatch(actions.models.setInternalModelField('speedrun', destination, 'moving', false));
          },
        }),
      );
    },
    saveField: (model, field, value) => {
      dispatch(actions.models.saveField(model, field, value));
    },
    newDraftModel: model => {
      dispatch(actions.models.newDraftModel(model));
    },
    deleteDraftModel: model => {
      dispatch(actions.models.deleteDraftModel(model));
    },
    updateDraftModelField: (type, pk, field, value) => {
      dispatch(actions.models.updateDraftModelField(type, pk, field, value));
    },
    saveDraftModels: models => {
      dispatch(actions.models.saveDraftModels(models));
    },
  };
}

export default connect(select, dispatch)(ScheduleEditor);
