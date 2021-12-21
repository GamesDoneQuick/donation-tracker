import { getSchedule, OengusSchedule } from 'oengus-api';
import React, { useState } from 'react';
import { useSelector } from 'react-redux';
import { useParams } from 'react-router';
import { Event } from '../../tracker/events/EventTypes';
import styles from './scheduleImport.mod.css';
import { ScheduleImportCore } from './scheduleImportCore';
import { ScheduleImportTable } from './scheduleImportTable';

const ScheduleImport: React.FC = () => {
  const { event: eventId } = useParams<{ event: string | undefined }>();
  const event = useSelector<any, Event>((state: any) => state.models.event?.find((e: any) => e.pk === +eventId!));

  const [loading, setLoading] = useState<boolean>(false);
  const [slug, setSlug] = useState<string>();
  const [schedule, setSchedule] = useState<OengusSchedule | null>(null);

  const handleAction = async (callback: () => Promise<void>) => {
    setLoading(true);

    try {
      await callback();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleChangeSlug = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSlug(e.target.value);
  };

  const loadOengusSchedule = async () => {
    if (slug) {
      handleAction(async () => {
        const oengusSchedule = await getSchedule(slug);
        setSchedule(oengusSchedule);
      });
    }
  };

  return (
    <div>
      <h3>{event?.name}</h3>

      <div>
        <div className={styles.formInput}>
          <label>
            Oengus slug
            <input type="text" name="oengus-slug" id="oengus-input-slug" onChange={handleChangeSlug} />
          </label>
          <button onClick={loadOengusSchedule} disabled={loading}>
            Load
          </button>
        </div>
      </div>

      <div className={styles.importTable}>{schedule && <ScheduleImportTable schedule={schedule} />}</div>

      <div className={styles.importCore}>{schedule && <ScheduleImportCore event={event} schedule={schedule} />}</div>
    </div>
  );
};

export default React.memo(ScheduleImport);
