import React, { useCallback, useEffect, useState } from 'react';
import moment from 'moment-timezone';
import { useParams } from 'react-router';
import usePromise from 'react-use-promise';

import { useConstants } from '@common/Constants';
import { JSONResponse, JSONResponseWithForbidden } from '@common/JSONResponse';
import { Ad, Interstitial, Interview, ModelFields, Run } from '@common/Models';
import { isServerError, ServerError } from '@common/Server';

import Table from './Table';

interface Person {
  permissions?: string[];
  username: string;
  staff?: boolean;
}

type Aggregate = [Interview[], Ad[] | ServerError, Run[], Person | ServerError];

export default function InterstitialEditor() {
  const { API_ROOT, CSRF_TOKEN } = useConstants();
  const { eventId } = useParams<{ eventId: string }>();
  const [promise, setPromise] = useState<Promise<Aggregate>>(new Promise(() => {}));
  const [saveError, setSaveError] = useState<ServerError | null>(null);
  const fetchAll = useCallback(() => {
    setPromise(
      Promise.all([
        fetch(`${API_ROOT}interviews/${eventId}/`).then(JSONResponseWithForbidden),
        fetch(`${API_ROOT}ads/${eventId}/`).then(JSONResponseWithForbidden),
        fetch(`${API_ROOT}search?type=run&event=${eventId}`).then(JSONResponse),
        fetch(`${API_ROOT}me`).then(JSONResponseWithForbidden),
      ]),
    );
    setSaveError(null);
  }, [API_ROOT, eventId]);
  useEffect(fetchAll, [fetchAll]);

  const moveInterstitial = useCallback(
    (sourceItem: Interstitial, destinationItem: Interstitial | Run) => {
      const formData = new FormData();
      let order;
      let suborder;

      if (destinationItem.fields.suborder) {
        order = destinationItem.fields.order;
        suborder = destinationItem.fields.suborder;
      } else if (sourceItem.fields.order >= destinationItem.fields.order) {
        order = destinationItem.fields.order - 1;
        suborder = -1; // special value, end of the list
      } else {
        order = destinationItem.fields.order;
        suborder = 1;
      }

      formData.append('id', `${sourceItem.pk}`);
      formData.append('model', sourceItem.model);
      formData.append('order', `${order}`);
      formData.append('suborder', `${suborder}`);
      fetch(`${API_ROOT}interstitial/`, {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': CSRF_TOKEN,
        },
      }).then(() => {
        fetchAll();
      });
    },
    [API_ROOT, CSRF_TOKEN, fetchAll],
  );

  const saveItem = useCallback(
    (fullId: string, fields: Partial<ModelFields>) => {
      const [model, id] = fullId.split('-');
      const formData = new FormData();
      Object.entries(fields).forEach(([k, v]) => {
        formData.append(k, `${v}`);
      });
      fetch(`${API_ROOT}${model.split('.')[1]}/${id}/`, {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': CSRF_TOKEN,
        },
      }).then(response => {
        if (response.ok) {
          fetchAll();
        } else {
          response.json().then(json => {
            setSaveError(json as ServerError);
          });
        }
      });
    },
    [API_ROOT, CSRF_TOKEN, fetchAll],
  );

  const [result, error, state] = usePromise(promise, [promise]);
  if (state === 'pending') return <>Loading...</>;
  if (error) {
    return (
      <div className="error">
        Could not fetch data:
        <br />
        {error.message}
        <br />
      </div>
    );
  }
  if (!result) {
    return <>shrug</>;
  }
  const interviews = result[0] as Interview[] | ServerError;
  const ads = result[1] as Ad[] | ServerError;
  const runs = result[2] as Run[];
  runs.forEach(r => {
    r.fields.setup_time = moment.duration(r.fields.setup_time);
    r.fields.run_time = moment.duration(r.fields.run_time);
  });
  const person = result[3] as Person | ServerError;
  const permissions = isServerError(person) ? [] : person.permissions || [];
  let interstitials: (Interview | Ad)[] = [];
  if (!isServerError(interviews)) {
    interstitials = interstitials.concat(interviews);
  }
  if (!isServerError(ads)) {
    interstitials = interstitials.concat(ads);
  }

  const canReorder = permissions.indexOf('tracker.change_interstitial') !== -1;
  interstitials = interstitials.map(i => ({ ...i, canReorder }));
  // TODO: this need a rework
  // const changeableModels = permissions
  //   .map(p => {
  //     const m = p.match(/(\w+).change_(\w+)/);
  //     return m && `${m[1]}.${m[2]}`;
  //   })
  //   .filter(p => !!p) as string[];
  return (
    <Table
      interstitials={interstitials}
      changeableModels={[]}
      runs={runs}
      moveInterstitial={canReorder ? moveInterstitial : null}
      saveItem={saveItem}
      saveError={saveError}
    />
  );
}
