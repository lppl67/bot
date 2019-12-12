-- $1 = user_id
-- $2 = tokens

UPDATE currency
SET tokens = tokens - $2
WHERE user_id = $1;