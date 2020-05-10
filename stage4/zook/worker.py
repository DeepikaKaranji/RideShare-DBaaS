import pika
from flask import Flask, jsonify, request, abort, make_response
from flask_sqlalchemy import SQLAlchemy
import json
import docker
import subprocess
import logging
import os
import uuid
import os
import time
import subprocess
import threading 
import sqlite3 as sqlite3
from kazoo.client import KazooClient
from kazoo.client import KazooState
logging.basicConfig()

new_master = 0

zk = KazooClient(hosts='zoo:2181',timeout=1.0)
zk.start(timeout=1)

cmd = "cat /proc/self/cgroup | grep 'docker' | sed 's/^.*\///' | tail -n1"
cid = subprocess.check_output(cmd,shell=True)
cid = cid.decode("utf-8")
cid=cid[0:12]

client2 = docker.APIClient()
pid = client2.inspect_container(cid)['State']['Pid']
print("---PID", pid)
print("---CID", cid)

zk.ensure_path("/worker")

if zk.exists("/worker/slave"):
    print("Slave exists")
else:
    zk.create("/worker/slave", b"hi")

if zk.exists("/worker/master"):
    present = 0
    print("Master exists")
    ms = "/worker/master"
    data, stat = zk.get(ms)
    data = data.decode("utf-8")
    ind = data.find('PID')
    pid_master = data[ind+5:len(data)+1]
    pid_master = int(pid_master)
    print("HELLO FROM MASTERKK - ",pid_master)
    data,stat = zk.get("/worker/master")
    data = data.decode("utf-8")
    ind = data.find('CID')
    mcid = data[ind+6:ind+18]
    if(mcid == cid):
        present = 1
        pid = pid_master

    sl = zk.get_children("/worker/slave")  
    for i in range(0,len(sl)):
        nm ="/worker/slave/"+sl[i]
        data, stat = zk.get(nm)
        data = data.decode("utf-8")
        ind = data.find('CID')
        ccid = data[ind+6:ind+18]
        ind = data.find('PID')
        cpid = data[ind+6:len(data)+1]
        if(ccid == cid):
            present = 1
            pid = cpid
            

    if(present == 0):
        data1 = "I am slaver CID : "+cid+" PID : "+str(pid)
        data2 = data1.encode()
        zk.create("/worker/slave/slave"+str(pid), data2, ephemeral = True)

    else:
        new_master = 1
        
else:
    data1 = "I am master CID : "+cid+" PID : "+str(pid)
    data2 = data1.encode()
    zk.create("/worker/master", data2,ephemeral = True)
    
connection = pika.BlockingConnection(pika.ConnectionParameters(host='rmq'))
channel = connection.channel()


zk = KazooClient(hosts='zoo:2181',timeout=1.0)
zk.start(timeout=1)

ms = "/worker/master"
data, stat = zk.get(ms)
data = data.decode("utf-8")
ind = data.find('PID')
pid_master = data[ind+5:len(data)+1]
pid_master = int(pid_master)
ind = data.find('CID')
cid_master = data[ind+5:ind+18]


if(new_master == 0):
# current worker pid
    cmd = "cat /proc/self/cgroup | grep 'docker' | sed 's/^.*\///' | tail -n1"
    cid = subprocess.check_output(cmd,shell=True)
    cid = cid.decode("utf-8")
    cid=cid[0:12]
    client2 = docker.APIClient()
    pid = client2.inspect_container(cid)['State']['Pid']
    pid = int(pid)


print("~~~~~~~~~~~~~~~~ZNODE MASTER PATH PID", pid_master)
print("~~~~~~~~~~~~~~~~CURRENT WORKER PID", pid)
print("~~~~~~~~~~~~~~~~ZNODE MASTER PATH CID", cid_master)
print("~~~~~~~~~~~~~~~~CURRENT WORKER CID", cid)

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+str(pid)+'.db'
db = SQLAlchemy(app)
dbname = str(pid)+'.db'

class user_details(db.Model):
    username = db.Column(db.String(80), primary_key=True)
    password = db.Column(db.String(80))

class ride_details(db.Model):
    rideid = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    timestamp = db.Column(db.String(80))
    source = db.Column(db.Integer)
    destination = db.Column(db.Integer)
class join_user(db.Model):
    srn= db.Column(db.Integer,primary_key=True)
    rideid = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80),primary_key=True)
class signal_table(db.Model):
    srn= db.Column(db.Integer,primary_key=True)
    cleardb_flag = db.Column(db.Integer)

db.create_all()


if(pid_master != pid):
    master = -1 #it is slave
else:
    master = 0 #it is master
# master = data1.find("master")
print("************************NEW_MASTER",new_master)

if((master == -1)and(new_master==0)):
    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    print("IN SLAVE")
    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    def slave_function(event):
        print("IN SLAVE FUNCTION event",event)
        print("SLAVE FUNCTION CALLED")
        if(event.type == 'CHANGED'):
            print("you have succeeded, no new container was spawned")
        elif(event.type == 'DELETED'):
            global pid
            print("----Deleting DB of Worker with PID "+str(pid)+"----")
            time.sleep(10)
            while(not zk.exists("/worker/master")):
                print("WAITING FOR MASTER")
            ms = "/worker/master"
            data, stat = zk.get(ms)
            print("DATAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", data)
            data = data.decode("utf-8")
            ind = data.find('PID')
            pid = data[ind+5:len(data)+1]
            masterdb = str(pid)+".db"
            print("MASTER DB---------------", masterdb)
    
            print("---------Spawning New Slave!!--------")
            client = docker.from_env()
            new_container = client.containers.create(
                image = "zook_worker:latest",
                command = "python /code/worker.py",
                volumes = {
                    '/var/run/docker.sock': {'bind':'/var/run/docker.sock', 'mode':'rw'},
                    '/cloud/stage4/zook':{'bind':'/code', 'mode':'rw'}    
                },
                network = "zook_default",
                detach = True
            )
            print("Trying to start a new container")
            new_container.start()
            print("NEW CONTAINER--", new_container)
    
            # copy to new container db from master db
            new_cid = new_container.id
            client2 = docker.APIClient()
            new_pid = client2.inspect_container(new_cid)['State']['Pid']

            print("############ PID NEW CONTAINER--", new_pid)
            print("----------To copy: masterdb, newdb ", masterdb, str(new_pid))
            cmd = "cp "+ masterdb +" "+ str(new_pid)+".db"
            res = os.system(cmd)
    
        else:
            print("Uh what event is this even??")
       
    if zk.exists("/worker/slave/slave"+str(pid)):
        children = zk.get("/worker/slave/slave"+str(pid), watch=slave_function)

    channel.queue_declare(queue='rpcq', durable = True)
    channel.exchange_declare(exchange='logs', exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange='logs', queue=queue_name)

    def callback_sync(ch, method, properties, body): 
        print(" [x] Received %r" % body)
        x=json.loads(body)
        data = x["insert"]
        cn = x["column"]
        tn = x["table"]
        if(tn == "signal_table"):
            ride_details.query.delete()
            db.session.commit()
            print("ride cleared")

            user_details.query.delete()
            db.session.commit()
            print("ride cleared")

            join_user.query.delete()
            db.session.commit()
            print("join users cleared")

        else:
            tn=eval(tn) 
            new_user=tn()
            for i in range(len(data)):
                data1 = data[i]
                c1 = cn[i]
                setattr(new_user, c1, data1)
            db.session.add(new_user)
            db.session.commit()        
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d.values()

    def callback_read(x): 
        print(" [x] Received IN READ%r" % x)
        print("======================")
        print("PID: ", str(pid))
        print("======================")
        data = x["where"]
        cn = x["column"]
        tn = x["table"]
        print(data,cn,tn)
        if(data == "fetchall"):
            
            with app.app_context():
                print("FETCHING ALL USERS----------")
                # flatlist = []
                # tn = eval(tn)
                # userlist = tn.query.all()
                # print("---------usrlist--", \
                #     userlist, "--type--", type(userlist[0]))

                # for user in userlist:
                #     print("--user--", user,"--type--", type(user)) <user_details aaa>
                #     flatlist.append(user)
                conn = sqlite3.connect(dbname)
                conn.row_factory = dict_factory
                cur = conn.cursor()
                all = cur.execute("SELECT username FROM user_details;").fetchall()
                print ("all ----------------", all)
                flatlist = [ item for elem in all for item in elem]
                print ("---flatlist---", flatlist)
                return make_response(jsonify(flatlist), 200)
        else:
            print("NOT FETCH----------")
            tn=eval(tn) 
            new_user=tn()
            result = data.find('AND') 
            if(result==-1):
                ind = data.find('=')
                att = data[:ind-1]
                val = data[ind+2:]
                x = getattr(tn, att)
                user1= tn.query.filter((x == val)).all()
                d = {}
                for i in user1:
                    cnt = 0
                    for j in cn:
                        if j not in d:
                            d[j] =[]
                            cnt =cnt+1
                        a = getattr(i, j)
                        d[j].append(a)
            
            else:
                q1 = data[:result-1]
                q2 = data[result+4:]
                i1 = q1.find('=')
                a1 = q1[:i1-1]
                v1 = q1[i1+2:]
                x1 = getattr(tn, a1)
                i2 = q2.find('=')
                a2 = q2[:i2-1]
                v2 = q2[i2+2:]
                x2 = getattr(tn, a2)
                user1= tn.query.filter(x1 == v1).filter(x2 == v2).all()
                d = {}
                for i in user1:	
                    cnt = 0
                    for j in cn:
                        if j not in d:
                            d[j] =[]
                            cnt =cnt+1
                        a = getattr(i, j)
                        d[j].append(a)
            return d
            ch.basic_ack(delivery_tag = method.delivery_tag) 
     

    def on_request(ch, method, props, body):
        print(" [x] Received IN REQUEST %r" % body)
        x=json.loads(body)
        response = callback_read(x)
 
        ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=str(response))
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(
        queue=queue_name, on_message_callback=callback_sync, auto_ack=True)

    channel.basic_consume(queue='rpcq', on_message_callback=on_request)
    print(' [*] Waiting for messages. To exit press CTRL+C')

else:
    new_master = 0

    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    print("IN MASTER")
    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")

    channel.queue_declare(queue='wq',durable = True)

    def callback_write(ch, method, properties, body): 
        print(" [x] Received %r" % body)
        print("======================")
        print("MASTER WRITE PID^^^^^^^^^^^^^^^^^^^^^")
        print("======================")
        x=json.loads(body)
        data = x["insert"]
        cn = x["column"]
        tn = x["table"]
        if(tn == "signal_table"):
            ride_details.query.delete()
            db.session.commit()
            print("ride cleared")

            user_details.query.delete()
            db.session.commit()
            print("ride cleared")

            join_user.query.delete()
            db.session.commit()
            print("join users cleared")

        else:
            tn=eval(tn) 
            new_user=tn()
            for i in range(len(data)):
                data1 = data[i]
                c1 = cn[i]
                setattr(new_user, c1, data1)
            db.session.add(new_user)
            db.session.commit()
        ch.basic_ack(delivery_tag = method.delivery_tag)
        channel.exchange_declare(exchange='logs',
                         exchange_type='fanout')
        message = body
        channel.basic_publish(exchange='logs', routing_key='', body=message)
        print(" [x] Sent %r" % message)
     
    channel.basic_consume(queue='wq', on_message_callback=callback_write)
    print(' [*] Waiting for messages. To exit press CTRL+C')

channel.start_consuming() 

