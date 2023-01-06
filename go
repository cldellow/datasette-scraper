kill $(ps aux|grep pyth|grep hupper|awk '{print $2}')
# You can use strace to monitor how many write locks are required;
# useful when making changes to minimize lock contention
# ./go |& grep --line-buffered WRLCK
#strace -f --trace fcntl datasette --reload --root --metadata metadata.json "$@" shopify.db
datasette --reload --port 8181 --root --metadata metadata.json "$@" test.db
