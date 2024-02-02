
import schedule
import time
from db_exec import PSQL_CONN,MONGO,CH
import logging
import datetime

''' 
for daemon setup script
create  - >> "mcedit /etc/systemd/system/cron_dispetcher_icmp.service"
copy in cron_dispetcher_icmp.service ->> 
_______________________________

[Unit]
Description=Collecting metrics ping for dispetcher to CH

[Service]
ExecStart=/usr/bin/python3 /opt/cron/dispetcher/icmp/icmp_main.py
WorkingDirectory=/opt/cron/dispetcher/icmp/
StandardOutput=file:/var/log/cron_dispetcher/icmp_output.log
StandardError=file:/var/log/cron_dispetcher/icmp_error.log
Restart=always

[Install]
WantedBy=multi-user.target

_________________________________

<<----cron_dispetcher_icmp.service

run next commands -->>>
_____________________________

sudo systemctl daemon-reload
sudo systemctl enable cron_dispetcher_icmp.service
sudo systemctl start cron_dispetcher_icmp.service

______________________________

<<--- run next commands

'''




"""
'id' managed_object_profile for get data, if you need to find out the number of id,
execute the next query from postgresql - 'select id,name from sa_managedobjectprofile;'
There you'll need to choose only for check stack status profiles
"""

n = None
segments_list = ['p/pe','core','m-dsw'] # this list for include specific "network segment" from noc to listen in this app
my_inventory = [] # zero inventory for starting this app
#'i' - for correct job scheduler. It's need when you start the service , 'my_inventory' is empty yet, and it's nesseccery to fill it
#'i' - use here like starting point
i = 0

class INVENTORY():

    def __init__(self,id_list):
        self.id_list = id_list



    def start_job_inventory(self,*args):
            mongo = MONGO(n, self.id_list)
            collect = mongo.get_segment_id()
            id_list1 = ""
            for i in collect:
                obj_segment_id = i["id"]
                id_list1 = id_list1+f"'{obj_segment_id}',"
            id_list1 = id_list1.rstrip(",")
            psql = PSQL_CONN(id_list1,n)
            process = psql.postgre_conn_inv()
            global my_inventory
            result = (self.collect_inv(process,collect))
            return result


    def collect_inv(self,inventory,segment_dict):
            dict_result = []
            for r in inventory:
                dict = {}
                obj_id = r[0]
                obj_name = r[1]
                obj_ip = r[2]
                obj_bi_id = r[3]
                obj_segment_id = r[4]
                for d in segment_dict:
                    if obj_segment_id == d['id']:
                        obj_segment_name = d['name']
                        obj_segment_id = d['id']
                        dict.update({"obj_id": obj_id, "obj_ip_address": obj_ip,
                                        "obj_name": obj_name,
                                        "obj_segment": obj_segment_name, "obj_bi_id": obj_bi_id})
                dict_result.append(dict)
            return dict_result



def calculate_alarm(alarm_list, target_list):
    new_list = []
    alarm_dict = {item['obj_id']: item['obj_result'] for item in alarm_list}
    if alarm_list:
        for target in target_list:
            t_id = target['obj_id']
            if t_id in alarm_dict:
                target['obj_result'] = alarm_dict[t_id]
                new_list.append(target)
            else:
                new_list.append(target)
    else:
        new_list.extend(target_list)
    return new_list



def executer_run():
    try:

        for item in my_inventory:
           item['obj_result'] = 3
        mongodb = MONGO()
        alarm_list = mongodb.get_alarm()
        new_list = calculate_alarm(alarm_list,my_inventory)
        ch = CH(new_list)
        result = ch.ch_insert()
    except Exception as err:
        logging.warning(f'\n\n{datetime.datetime.now()}\n\n{err}')


int = INVENTORY(segments_list)
schedule.every(60).seconds.do(executer_run)
schedule.every(2).hours.do(int.start_job_inventory)

while i == 0:
    my_inventory = int.start_job_inventory(segments_list)
    time.sleep(1)
    i = i+1
while i == 1:
    try:
        schedule.run_pending()
        time.sleep(1)
    except Exception as err:
        logging.warning(f'\n\n{datetime.datetime.now()}\n\n{err}')

