kill $(ps aux|grep pyth|grep hupper|awk '{print $2}')
datasette --reload --root test.db
