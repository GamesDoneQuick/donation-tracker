import moment from 'moment';
import { OengusRunLine, OengusSchedule, OengusSetupLine, OengusUser } from 'oengus-api';
import React, { useState } from 'react';
import { Model, Run, Runner } from '../../common/Models';
import { Event } from '../../tracker/events/EventTypes';
import HTTPUtil from '../../public/util/http';
import Endpoints from '../../tracker/Endpoints';
import _ from 'lodash';

type Props = {
  event: Event;
  schedule: OengusSchedule;
};

export const ScheduleImportCore = ({ event, schedule }: Props) => {
  const [process, setProcess] = useState<'before' | 'runners' | 'schedules' | 'done'>('before');
  const [imported, setImported] = useState<number>(0);

  const makeRun = (line: OengusRunLine | OengusSetupLine, index: number): Run => {
    const categoryTooLong = line.categoryName ? line.categoryName.length > 64 : false;
    return {
      pk: -1,
      model: 'tracker.speedrun',
      canReorder: true,
      fields: {
        display_name: `${line.gameName || 'Unknown'} ${line.categoryName || 'Unknown'}`,
        name: line.gameName || 'Unknown',
        category: !categoryTooLong ? line.categoryName || 'Unknown' : 'Too long name',
        console: line.console,
        starttime: null,
        endtime: null,
        run_time: moment.duration(line.estimate),
        setup_time: moment.duration(line.setupTime),
        order: index + 1,
      },
    };
  };

  const makeRunners = (schedule: OengusSchedule): { model: Runner; origin: OengusUser }[] => {
    const runners = schedule.lines
      .flatMap(line => line.runners)
      .filter((runner, index, runners) => runners.findIndex(r => r.id === runner.id) === index);

    return runners.map(runner => ({
      model: {
        pk: -1,
        model: 'tracker.runner',
        canReorder: false,
        fields: {
          name: runner.usernameJapanese || runner.username,
          twitter: runner.connections.find(conn => conn.platform === 'TWITTER')?.username,
          twitch: runner.connections.find(conn => conn.platform === 'TWITCH')?.username,
          nico: runner.connections.find(conn => conn.platform === 'NICO')?.username,
          platform: 'TWITCH',
          pronouns: runner.pronouns,
        },
      },
      origin: runner,
    }));
  };

  const saveModel = (model: Model, type: string) => {
    const url = model.pk < 0 ? Endpoints.ADD : Endpoints.EDIT;

    const omitKeys = Object.entries(model.fields)
      .filter(([k, v]) => {
        return v === null;
      })
      .map(([k, v]) => {
        return k;
      });

    return HTTPUtil.post(
      url,
      {
        type,
        id: model.pk,
        ..._.omit(model.fields, omitKeys),
      },
      {
        encoder: HTTPUtil.Encoders.QUERY,
      },
    );
  };

  const postSchedules = async () => {
    setProcess('runners');

    const savedRunners: { [pk: number]: Runner } = [];
    setImported(0);
    const runners = makeRunners(schedule);
    const runnerPromises = runners.map(({ model, origin }) => {
      return saveModel(model, 'runner')
        .then(res => {
          const saved = res[0] as Runner;

          savedRunners[origin.id] = saved;
          setImported(prev => prev + 1);
          return Promise.resolve();
        })
        .catch(e => {
          console.error('failed to import:');
          console.error(model);
          console.error(e.body);
          throw e;
        });
    });

    Promise.allSettled(runnerPromises)
      .then(results => {
        if (results.some(result => result.status === 'rejected')) {
          return Promise.reject();
        }
        setImported(0);
        setProcess('schedules');
        const runPromises = schedule.lines.map((line, index) => {
          const run = makeRun(line, index);
          const fields = Object.assign(run.fields, {
            run_time: `${run.fields.run_time.hours()}:${run.fields.run_time
              .minutes()
              .toString()
              .padStart(2, '0')}:${run.fields.run_time.seconds().toString().padStart(2, '0')}`,
            setup_time: `${run.fields.run_time.hours()}:${run.fields.setup_time
              .minutes()
              .toString()
              .padStart(2, '0')}:${run.fields.run_time.seconds().toString().padStart(2, '0')}`,
            runners: line.runners.map(runner => savedRunners[runner.id].pk).join(','),
          });
          run.fields = fields;
          return saveModel(run, 'run')
            .then(() => {
              setImported(prev => prev + 1);
            })
            .catch(e => {
              console.error('failed to import:');
              console.error(run);
              console.error(e.body);
            });
        });

        return Promise.allSettled(runPromises);
      })
      .finally(() => {
        setProcess('done');
      });
  };

  return (
    <div>
      <button onClick={postSchedules} disabled={['runners', 'schedules'].includes(process)}>
        Import
      </button>
      {process === 'runners' && (
        <p>
          importing runners: {imported} / {makeRunners(schedule).length}
        </p>
      )}
      {process === 'schedules' && (
        <p>
          importing speedruns: {imported} / {schedule.lines.length}
        </p>
      )}
    </div>
  );
};
