#         train by int100
#  https://github.com/int100/train
#
#      Under the MIT License
#

import json
import requests
import os
import time
import datetime
from prettytable import PrettyTable
from twilio.rest import Client as TClient

#----- constant module -----
get_station_names_url = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js"
get_ticket_infos_url = "https://kyfw.12306.cn/otn/leftTicket/queryZ?leftTicketDTO.train_date={}&leftTicketDTO.from_station={}&leftTicketDTO.to_station={}&purpose_codes=ADULT"
get_ticket_price_url = ""

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1"}

seats = {
        '商务座': 32,
        '一等座': 31,
        '二等座': 30,
        '特等座': 25,
        '软卧': 23,
        '硬卧': 28,
        '硬座': 29,
        '无座': 26
        }

stations = {}

# SMS
twilio_account_sid = ""
twilio_auth_token  = ""

message_to = ""
message_from = ""

client = TClient(twilio_account_sid, twilio_auth_token)

#----- utils module -----
def parse_stations(s):

    data = s.split("|")
    for i in range(0, int((len(data) - 1) / 5)):
        id_shorts = data[i * 5].split("@")
        id = -1
        shorts = id_shorts[1]
        if len(id_shorts) == 2:
            id = id_shorts[0]

        name = data[i * 5 + 1]
        short_name = data[i * 5 + 2]
        pinyin = data[i * 5 + 3]
        pinyin_short = data[i * 5 + 4]

        stations[name] = {
            "id": id, 
            "short": shorts, 
            "name": name, 
            "short_name": short_name,
            "pinyin": pinyin,
            "pinyin_short": pinyin_short 
            }

def get_station_names():
    s = ""
    if not os.path.exists("stations"):
        with open("stations", 'w', encoding='utf-8') as fd:
            stations = requests.get(get_station_names_url, headers=headers).text[20:-2]
            fd.write(stations)
            s = stations
    else:
        with open("stations", 'r', encoding='utf-8') as fd:
            s = fd.read()

    parse_stations(s)

def get_station(short_name):
    for i in stations:
        if stations[i]["short_name"] == short_name:
            return stations[i]

def get_train_infos(date, start, end):
    def parse(s):
        data = s.split("|")

        ticket = {
            "ticket_status": data[1],
            "train_no": data[2],
            "train_name": data[3],
            "train_start_station": data[4],
            "train_arrival_station": data[5],
            "train_start_time": data[8],
            "train_arrival_time": data[9],
            "train_cost_time": data[10],
            "train_status": data[11],
            "date": data[13],
            "tickets_status": {}
        }

        for i in seats:
            info = data[seats[i]]
            if info != "":
                ticket["tickets_status"][i] = info
            else:
                ticket["tickets_status"][i] = None
        return ticket

    url = get_ticket_infos_url.format(date, start, end)
    rep = requests.get(url, headers=headers).json()

    tickets = []
    for i in rep["data"]["result"]:
        tickets.append(parse(i))

    return tickets

if __name__ == "__main__":
    print("获取车站名中...")
    get_station_names()

    try:
        start = stations[input("请输入起始地（etc. 福州）：")]["short_name"]
        end = stations[input("请输入目的地（etc. 南京）：")]["short_name"]
    except:
        print("该站点不存在！")
        exit(0)

    date = input("请输入日期（F: yyyy-MM-dd）：")

    table = PrettyTable(["车次", "出发站", "到达站", "出发时间", "到达时间", "用时", "状态"])

    infos = get_train_infos(date, start, end)
    for i in infos:
        starts = get_station(i["train_start_station"])["name"]
        arrival = get_station(i["train_arrival_station"])["name"]
        if i["train_status"] != "Y" and i["train_status"] != "N":
            i["train_start_time"] = "-----"
            i["train_arrival_time"] = "-----"
            i["train_cost_time"] = "-----"
        
        table.add_row([i["train_name"], starts, arrival, i["train_start_time"], i["train_arrival_time"], i["train_cost_time"], i["ticket_status"]])

    if len(infos) == 0:
        print("当天无车次！（{}-{}）".format(start, end))
    else:
        print(table)
        trainno = input("请输入车次查询车票状态（etc. D3136）：")
        
        while True:
            info = get_train_infos(date, start, end)
            for i in info:
                if i["train_name"] == trainno:
                    seat = i["tickets_status"]
                    second = seat['二等座']

                    s = get_station(i["train_start_station"])["name"]
                    a = get_station(i["train_arrival_station"])["name"]

                    t = i["train_start_time"]
                    print("一等座：{}, 二等座：{}, 无座：{} （{}）\n".format(first, second, none, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    if second:
                        message = client.messages.create(
                            to=message_to, 
                            from_=message_from,
                            body="【TSH】车次 {} （{}-{} 开点 {} {} ）有余票：二等座 {}".format(trainno, s, a, date, t, second))
                        exit(0)
            time.sleep(0.5)
