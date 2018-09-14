cd stats_reported
jq -r \
	'"\(.tag)-\(.serial_number), \"\(.timestamp)\", \(.seconds)"' \
	start_up_time.jsonl screen_cache_time.jsonl \
| sort | tee /dev/tty | xclip -selection clipboard
echo "Output copied to clipboard."