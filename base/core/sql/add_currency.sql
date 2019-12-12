-- $1 = user_id
-- $2 = tokens

INSERT INTO currency (user_id, tokens)
VALUES ($1, $2)
ON CONFLICT (user_id)
DO
    UPDATE
        SET tokens = currency.tokens + excluded.tokens;