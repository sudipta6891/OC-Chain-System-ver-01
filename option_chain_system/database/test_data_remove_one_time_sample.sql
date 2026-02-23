#ONE TIME RUN IN PGADMIN TO DELETE TEST DATA--> CHANGE DATE, TIME PROPERLY BEFORE RUNNING
BEGIN;

DELETE FROM option_chain_snapshot
WHERE snapshot_time >= '2026-02-18 16:00:00+05:30'
  AND snapshot_time <  '2026-02-19 09:00:00+05:30';

DELETE FROM option_chain_summary
WHERE snapshot_time >= '2026-02-18 16:00:00+05:30'
  AND snapshot_time <  '2026-02-19 09:00:00+05:30';

DELETE FROM scalp_score_tracking
WHERE snapshot_time >= '2026-02-18 16:00:00+05:30'
  AND snapshot_time <  '2026-02-19 09:00:00+05:30';

COMMIT;
