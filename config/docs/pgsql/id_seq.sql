-- https://gist.github.com/beginor/9d9f90bc58e1313f6aecd107f8296732
-- https://github.com/falcondai/python-snowflake/blob/master/snowflake.py
-- https://www.jianshu.com/p/e664ce409a25
CREATE SEQUENCE global_id_sequence START WITH 1024;
ALTER SEQUENCE global_id_sequence RESTART WITH 1024;

CREATE OR REPLACE FUNCTION id_generator(OUT result bigint) AS $$
DECLARE
    our_epoch bigint := 1291957293056;
    seq_id bigint;
    now_millis bigint;
    shard_id int := 5;
BEGIN
    -- there is a typo here in the online example, which is corrected here
    SELECT nextval('global_id_sequence') % 1024 INTO seq_id;

    SELECT FLOOR(EXTRACT(EPOCH FROM clock_timestamp()) * 1000) INTO now_millis;
    result := (now_millis - our_epoch) << 23;
    result := result | (shard_id << 10);
    result := result | (seq_id);
END;
$$ LANGUAGE PLPGSQL;
