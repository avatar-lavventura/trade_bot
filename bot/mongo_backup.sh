#!/bin/bash

URL="https://@ppp.woelkli.com"
MONGO_DIR=$HOME/Nextcloud/mongodb_backup
DIR=$PWD
SCRATCH_DIR=$HOME/mongodb_backup
date=$(date '+%d_%m_%y')

cd $MONGO_DIR
strings=("usdt" "btc")
for var in "${strings[@]}"; do
    fn=$SCRATCH_DIR/"${var:?}"
    rm -rf $fn
    mongodump -d $var -o ~/mongodb_backup
    tar czfP ${date}_${var}".tar.gz" $fn && rm -rf ~/Nextcloud/mongodb_backup/$var
done
cd $DIR

FILE=~/.nc
if [ -f "$FILE" ]; then
    # upload
    username=$(grep username ~/.nc | awk -F" " '{print $2}')
    passwd=$(grep password ~/.nc | awk -F" " '{print $2}')
    nextcloudcmd -s -n -u $username -p $passwd -h ~/Nextcloud $URL
    echo "done"
fi
