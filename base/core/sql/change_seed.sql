-- $1 = user_id
-- $2 = seed

INSERT INTO currency (user_id, tokens, seed)
VALUES ($1, 0, $2)
ON CONFLICT (user_id)
DO
    UPDATE
        SET seed = excluded.seed;