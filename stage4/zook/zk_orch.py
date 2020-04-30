from flask import Flask, jsonify, request, abort, make_response
from flask_sqlalchemy import SQLAlchemy
import json
import docker
import uuid
import pika
import os
import time
import logging
import subprocess
import requests
import threading 
from kazoo.client import KazooClient
from kazoo.client import KazooState
logging.basicConfig()

print("HI ORCH")

app = Flask(__name__)
flag = 0
count = 0
zk = KazooClient(hosts='zoo:2181',timeout=1.0)
zk.start(timeout=1)




def master_function(event):
    print("IN MASTER")
    print(event)
    children = zk.get_children("/worker")
    sl = zk.get_children("/worker/slave")    
    if(event.type == 'DELETED'):
        nm ="/worker/slave/"+sl[0]
        data, stat = zk.get(nm)
        data = data.decode("utf-8")
        ind = data.find('PID')
        pid = data[ind+5:len(data)+1]
        min_pid=int(pid)
        ind = data.find('CID')
        min_cid = data[ind+6:ind+18]
      
        for i in range(1,len(sl)):
            nm ="/worker/slave/"+sl[i]
            data, stat = zk.get(nm)
            data = data.decode("utf-8")
            ind = data.find('PID')
            pid = data[ind+5:len(data)+1]
            pid=int(pid)
            if(pid<min_pid):
                min_pid=pid
                ind = data.find('CID')
                cid = data[ind+6:ind+18]
                min_cid = cid
        client = docker.from_env()
        container = client.containers.get(min_cid)
        children = zk.get_children("/worker")
        data1 = "I am master CID : "+min_cid+" PID : "+str(min_pid)
        data1 = data1.encode()
        zk.create("/worker/master", data1,ephemeral=True)
        time.sleep(2)
        zk.delete("/worker/slave/slave"+str(min_pid), version=-1, recursive=False)

        # time.sleep(10)
        ms = "/worker/master"
        data, stat = zk.get(ms)
        data = data.decode("utf-8")
        ind = data.find('PID')

        ms = "/worker/master"
        data, stat = zk.get(ms)
        data = data.decode("utf-8")
        ind = data.find('PID')
        pid_master = data[ind+5:len(data)+1]
        pid_master = int(pid_master)


        # ind<0: if path/w/m isnt created not zk.exists("/worker/master") and 
        # min_pid!=pid_master: new master has not yet been elected
        while(min_pid!=pid_master):
            print("---------------------WHILE BEFORE RESTART-------------------")
            # update master_pid to break loop
            ms = "/worker/master"
            data, stat = zk.get(ms)
            data = data.decode("utf-8")
            ind = data.find('PID')
            pid_master = data[ind+5:len(data)+1]
            pid_master = int(pid_master)

        time.sleep(20)
        data,stat = zk.get("/worker/master")
        print("BEFORE RESTART MASTER DATA = ",data)
        container.restart()
        # 
        print("--------------AFTER RESTART MPID", pid_master)
        m = zk.get("/worker/master", watch=master_function)
        print(" MASTER after creating watch after restart-----------",m)#slave1


        # children = zk.get_children("/worker/slave")
        # print(" ALL SLAVES %s children with names %s" % (len(children), children))#slave1
        # children = zk.get_children("/worker")
        # print(" AFTER CHANGING %s children with names %s" % (len(children), children))#master,slave
        # print("SLAVE PID",min_pid)
        # print("SLAVE CID",min_cid)

begin = 0
if(begin == 0):
    children = zk.get("/worker/master", watch=master_function) 
    #global begin#
    print("IN BEGIN")
    print("BEGIN :", begin)

    begin = 1

@app.route("/api/v1/worker/list",methods=["GET"])
def list():
    l=[]
    ms = "/worker/master"
    data, stat = zk.get(ms)
    data = data.decode("utf-8")
    ind = data.find('PID')
    pid = data[ind+5:len(data)+1]
    print("--------------------MASTER-----------------------",pid)
    pid=int(pid)
    l.append(pid)
    sl = zk.get_children("/worker/slave")
    for i in sl:
        nm ="/worker/slave/"+i
        data, stat = zk.get(nm)
        data = data.decode("utf-8")
        ind = data.find('PID')
        pid = data[ind+5:len(data)+1]
        pid=int(pid)
        l.append(pid)
    l.sort()
    return make_response(json.dumps(l),200)

@app.route("/api/v1/crash/master",methods=["POST"])
def crash_master():
    m = "/worker/master"
    data, stat = zk.get(m)
    l=[]
    data = data.decode("utf-8")
    ind = data.find('PID')
    pid = data[ind+5:len(data)+1]
    pid=int(pid)
    l.append(pid)
    ind = data.find('CID')
    cid = data[ind+6:ind+18]
    zk.delete("/worker/master", version=-1, recursive=False)
    client = docker.from_env()
    container = client.containers.get(cid)
   # print(cid)
   # print(container)
    time.sleep(20)
    container.kill()
    children = zk.get_children("/worker")
    print(" IN ORCH AFTER CONTAINER KILL%s children with names %s" % (len(children), children))#master,slave
    children = zk.get_children("/worker/slave")
    print(" IN ORCH AFTER CONTAINER KILL%s children with names %s" % (len(children), children))#master,slave
    return make_response(json.dumps(l),200)

@app.route("/api/v1/crash/slave",methods=["POST"])
def crash_slave():
    maxi=0
    l=[]
    sl = zk.get_children("/worker/slave")
    for i in sl:
#        print("I" ,i)
        nm ="/worker/slave/"+i
        data, stat = zk.get(nm)
        data = data.decode("utf-8")
        ind = data.find('PID')
        pid = data[ind+6:len(data)+1]
        pid=int(pid)
        #print("PIDDDDD:   ", pid)
        if(pid>maxi):
            maxi=pid
            ind = data.find('CID')
            cid = data[ind+6:ind+18]
    l.append(maxi)
    zk.delete("/worker/slave/slave"+str(maxi), version=-1, recursive=False)
    client = docker.from_env()
    container = client.containers.get(cid)
#    print(cid)
#    print(container)
    time.sleep(20)
    container.kill()
    return make_response(json.dumps(l),200)


@app.route("/api/v1/db/write",methods=["POST"])
def write_db():
    data = request.get_json()["insert"]
    cn = request.get_json()["column"]
    tn = request.get_json()["table"]
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rmq'))
    channel = connection.channel()
    channel.queue_declare(queue='wq',durable = True)
    test= "{\"insert\": ["
    for i in range(0,len(data)-1):
        test= test+ "\"" +data[i] + "\"" + ","
    test= test + "\"" + data[len(data)-1] + "\"" 
    test =  test +"] , \"column\"" + ": [" 
    for i in range(0,len(cn)-1):
        test= test+ "\"" +cn[i] + "\"" + ","
    test= test + "\"" + cn[len(cn)-1] + "\"" 
    test =  test +"] , \"table\"" +":"+ "\"" + tn +"\"" +"}"
    channel.basic_publish(exchange='', routing_key='wq', body=test, properties=pika.BasicProperties(delivery_mode=2,))
    print(" [x] Sent %r" % test)
    connection.close()
    return {},200

class TestRpcClient(object):

    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='rmq'))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, n):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='',
            routing_key='rpcq',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=n)
        while self.response is None:
            self.connection.process_data_events()
        return self.response

def check():
    global flag
    flag = 0
    d={}
    sl = zk.get_children("/worker/slave")
    for i in sl:
        nm ="/worker/slave/"+i
        data, stat = zk.get(nm)
        data = data.decode("utf-8")
        ind = data.find('PID')
        pid = data[ind+5:len(data)+1]
        pid=int(pid)
        ind = data.find('CID')
        cid = data[ind+6:ind+18]
        d[pid] = cid
    c=d.keys() 
    print("DICT: ",d)
    l=[]
    for i in c:
        l.append(i)
    print("LIST: ",l)
    l.sort()
    l.reverse()
    n = len(l)  #no.of slaves
    global count
    if(count==0):
        no = 1 #total no.of slaves we want
    elif(count%20 == 0):
        no = count//20
    else:
        no = count//20 +1
    todo = no - n
    print("-----------SLAVES WE HAVE-----------",n)
    print("----------TOTAL SLAVES WE NEED------------",no)
    print("-----------TODO-----------",todo)
    if( todo > 0):
        i=0
        ms = "/worker/master"
        data, stat = zk.get(ms)
        data = data.decode("utf-8")
        ind = data.find('PID')
        pid = data[ind+5:len(data)+1]
        masterdb = str(pid)+".db"
        print("MASTER DB---------------", masterdb)
        while(i<todo):
            client = docker.from_env()
            print("VALUE OF I",i)
            new_container = client.containers.create(
                image = "zook_worker:latest",
                command = "python /code/worker.py",
                volumes = {
                    '/var/run/docker.sock': {'bind':'/var/run/docker.sock', 'mode':'rw'},
                    '/home/dpk/Desktop/FINALFINALFINAL/zook':{'bind':'/code', 'mode':'rw'}    
                },
                network = "zook_default",
                detach = True
            )
            print("Trying to start a new container")
            new_container.start()
            # print(new_container.logs())
            print("--------NEW CONTAINER--------", new_container)
   
            # copy to new container db from master db
            new_cid = new_container.id
            client2 = docker.APIClient()
            new_pid = client2.inspect_container(new_cid)['State']['Pid']
            print("-----new container pid-----", new_pid)
            cmd = "cp "+ masterdb +" "+ str(new_pid)+".db"
            # print("*********** COMMAND: ", cmd)
            res = os.system(cmd)
            i=i+1
    elif(todo < 0):
        todo = -todo     
        i=0
        while(i<todo):
            pid = l[i]
            cid = d[pid]
            zk.set("/worker/slave/slave"+str(pid), b"dummy data")
            res = os.system("rm "+str(pid)+".db")
            zk.delete("/worker/slave/slave"+str(pid), version=-1, recursive=False)
            client = docker.from_env()
            container = client.containers.get(cid)
            container.kill()
            i = i + 1   
  


@app.route("/api/v1/db/read",methods=["POST"])
def read_db():
    global flag
    global count
    if(flag == 0):
        count = 1
        flag = 1
        timer = threading.Timer(120.0, check) 
        timer.start() 
    else:
        count = count + 1
    print("+++++++++++++++++")
    print("COUNT",count)
    print("+++++++++++++++++")


    data = request.get_json()["where"]
    cn = request.get_json()["column"]
    tn = request.get_json()["table"]
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rmq'))
    channel = connection.channel()
    channel.queue_declare(queue='rq',durable=True)
    test= "{\"where\": "+"\"" + data + "\"" + ", \"table\"" +":"+ "\"" + tn + "\"" + ",\"column\" : [ "
    for i in range(0,len(cn)-1):
    	test= test+ "\"" +cn[i] + "\"" + ","
    test= test + "\"" + cn[len(cn)-1] + "\" ] }"
  #  channel.basic_publish(exchange='', routing_key='rq', body=test, properties=pika.BasicProperties(delivery_mode=2,))
    print(" [x] Sent %r" % test)
    test_rpc = TestRpcClient()
    result = test_rpc.call(test)
    print("RPC is %r" %result)
    connection.close()
    return {},200

if __name__ == "__main__":
    app.debug=True
    app.run(host="0.0.0.0",debug=True, use_reloader=False)
