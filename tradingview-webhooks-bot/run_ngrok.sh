#!/bin/bash

killall ngrok
LOCAL_PORT=5000
echo "Start ngrok in background on port [ $LOCAL_PORT ]"
nohup ngrok http 5000 --log=stdout > ngrok.log &
sleep 1
echo -n "Extracting ngrok public url ."
NGROK_PUBLIC_URL=""
while [ -z "$NGROK_PUBLIC_URL" ]; do
    # Run 'curl' against ngrok API and extract public (using 'sed' command)
    export NGROK_PUBLIC_URL=$(curl --silent --max-time 10 --connect-timeout 5 \
                                   --show-error http://127.0.0.1:4040/api/tunnels | \
                                  sed -nE 's/.*public_url":"https:..([^"]*).*/\1/p')
    sleep 1
    echo -n "."
done

echo "ngrok_public_url ==> http://$NGROK_PUBLIC_URL/webhook"
echo ""
tail -f ngrok.log
