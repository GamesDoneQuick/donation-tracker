import { fullKey, memoizeCallback } from '../../../../common/Util';
import React, { useState } from 'react';
import { Interview, InterviewFields } from '../../../../common/Models';
import { RowProps } from '../Rows';

const setStateCallback = memoizeCallback(
  (callback: (value: string) => void, _: string, event: React.ChangeEvent<HTMLInputElement>) => {
    callback(event.currentTarget.value);
  },
  (_: any, key: string) => key,
);
const setCheckedCallback = memoizeCallback(
  (callback: (value: boolean) => void, _: string, event: React.ChangeEvent<HTMLInputElement>) => {
    callback(event.currentTarget.checked);
  },
  (_: any, key: string) => key,
);

export interface InterviewRowProps extends RowProps {
  item: Interview;
}

export default React.memo(function InterviewRow({
  item,
  editing,
  editItem,
  saveItem: si,
  cancelEdit,
}: InterviewRowProps) {
  const saveItem = si as ((fields: Partial<InterviewFields>) => void) | null;
  const { fields } = item;
  const [interviewers, setInterviewers] = useState(fields.interviewers);
  const [interviewees, setInterviewees] = useState(fields.interviewees);
  const [subject, setSubject] = useState(fields.subject);
  const [producer, setProducer] = useState(fields.producer);
  const [camera_operator, setCameraOperator] = useState(fields.camera_operator);
  const [social_media, setSocialMedia] = useState(fields.social_media);
  const [clips, setClips] = useState(fields.clips);
  const [length, setLength] = useState(fields.length);
  const [saving, setSaving] = useState(false);
  return editing ? (
    <React.Fragment>
      <td>
        <input onChange={setStateCallback(setInterviewers, `${fullKey(item)}-interviewers`)} value={interviewers} />
      </td>
      <td>
        <input onChange={setStateCallback(setInterviewees, `${fullKey(item)}-interviewees`)} value={interviewees} />
      </td>
      <td>
        <input onChange={setStateCallback(setSubject, `${fullKey(item)}-subject`)} value={subject} />
      </td>
      <td>
        <input onChange={setStateCallback(setProducer, `${fullKey(item)}-producer`)} value={producer} />
      </td>
      <td>
        <input
          onChange={setStateCallback(setCameraOperator, `${fullKey(item)}-camera_operator`)}
          value={camera_operator}
        />
      </td>
      <td>
        <input
          type="checkbox"
          onChange={setCheckedCallback(setSocialMedia, `${fullKey(item)}-social_media`)}
          checked={social_media}
        />
      </td>
      <td>
        <input type="checkbox" onChange={setCheckedCallback(setClips, `${fullKey(item)}-clips`)} checked={clips} />
      </td>
      <td>
        <input onChange={setStateCallback(setLength, `${fullKey(item)}-length`)} value={length} />
      </td>
      <td>
        <button
          onClick={() => {
            saveItem!({
              interviewers,
              interviewees,
              subject,
              producer,
              camera_operator,
              social_media,
              clips,
              length,
            });
            setSaving(true);
          }}>
          Save
        </button>
        <button onClick={cancelEdit!}>Cancel</button>
      </td>
    </React.Fragment>
  ) : (
    <React.Fragment>
      <td>{subject}</td>
      <td>{interviewers}</td>
      <td>{interviewees}</td>
      <td>{producer}</td>
      <td>{camera_operator}</td>
      <td>
        <input type="checkbox" disabled={true} checked={social_media} />
      </td>
      <td>
        <input type="checkbox" disabled={true} checked={clips} />
      </td>
      <td>{length}</td>
      {editItem ? <td>{saving ? 'Saving...' : <button onClick={editItem}>Edit</button>}</td> : null}
    </React.Fragment>
  );
});
