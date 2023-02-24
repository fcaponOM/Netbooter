sudo mount -o remount,rw /

set -x

op=$1
platform="$2"
mac=$(ifconfig eth0 | grep -o -E ..:..:..:..:..:..)
ip=$(hostname -I)

timestamp="`date '+%Y-%m-%d %H:%M:%S'`"

thirdoct=`echo $ip | awk '{split($0,i,"."); print i[3]}'`

if [ $thirdoct = '192' ];
then
   echo "Getting client files from Openmotics Cloud for $mac - $ip"
   /usr/bin/python /opt/openmotics/install/get_client.py $mac $op >> /tmp/boot.log

    echo > /etc/issue
    welcome="Welcome to the OpenMotics Gateway\n\nYour registration key:"
    echo "$welcome $(grep uuid /opt/openmotics/etc/openmotics.conf | awk -v N=3 '{print $N}') \n\n" >> /etc/issue
    echo "" >> /etc/issue

    pass=$(grep cloud_pass /opt/openmotics/etc/openmotics.conf | awk -v N=3 '{print $N}')
    echo "root:$pass" | sudo chpasswd

    if [ $platform == "staging" ]; then
        sed -i '3s,.*,vpn_check_url = https://staging.openmotics.com/api/gateway/heartbeat,' /opt/openmotics/etc/openmotics.conf
        sed -i '4s,.*,remote staging.openmotics.com 1194,' /etc/openvpn/client/omcloud.conf
    fi


    echo "Waiting for services to restart"
    for i in {60..1}
    do
    echo -n "$i "
    sleep 1
    done
    echo

    echo "Attempting EEPROM wipe"
    curl -v -F data=@/opt/openmotics/install/master.eep 127.0.0.1/master_restore
fi
