import React from 'react';
import { connect } from 'react-redux';

import { useConstants } from '@common/Constants';
import { actions } from '@public/api';
import { hasPermission } from '@public/api/helpers/auth';
import useSafeDispatch from '@public/api/useDispatch';
import { useEventParam } from '@public/apiv2/reducers/trackerApi';
import Spinner from '@public/spinner';

import { setAPIRoot } from '@tracker/Endpoints';

import SpeedrunTable from './speedrunTable';

class ScheduleEditor extends React.Component {
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

const Connected = connect(select, dispatch)(ScheduleEditor);

export default function Wrapped() {
  const eventId = useEventParam();
  const [ready, setReady] = React.useState(false);
  const { API_ROOT } = useConstants();
  const dispatch = useSafeDispatch();

  React.useLayoutEffect(() => {
    setAPIRoot(API_ROOT);
    setReady(true);
  }, [API_ROOT]);

  React.useEffect(() => {
    if (ready) {
      dispatch(actions.singletons.fetchMe());
    }
  }, [dispatch, ready]);
  return ready ? <Connected eventId={eventId} /> : null;
}
