from flask import Flask, jsonify, request, abort, make_response
from flask_sqlalchemy import SQLAlchemy
import json
import docker
import uuid
import pika
import time
import logging

from kazoo.client import KazooClient
from kazoo.client import KazooState
logging.basicConfig()

print("HI ORCH")

app = Flask(__name__)

zk = KazooClient(hosts='zoo:2181',timeout=1.0)
zk.start(timeout=1)


@app.route("/api/v1/worker/list",methods=["GET"])
def list():
    l=[]
    ms = "/worker/master"
    data, stat = zk.get(ms)
    data = data.decode("utf-8")
    ind = data.find('PID')
    pid = data[ind+5:len(data)+1]
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
    print(cid)
    print(container)
    time.sleep(20)
    children = zk.get_children("/worker")
    print(" IN ORCH %s children with names %s" % (len(children), children))#master,slave
    children = zk.get_children("/worker/slave")
    print(" IN ORCH %s children with names %s" % (len(children), children))#master,slave
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
        print("PIDDDDD:   ", pid)
        if(pid>maxi):
            maxi=pid
            ind = data.find('CID')
            cid = data[ind+6:ind+18]
    l.append(maxi)
    zk.delete("/worker/slave/slave"+str(maxi), version=-1, recursive=False)
    client = docker.from_env()
    container = client.containers.get(cid)
    print(cid)
    print(container)
    # delete db
    print("----Deleting DB of Worker with PID "+str(maxi)+"----")
    res = os.system("rm "+str(maxi)+".db")
    print("deleted res: ", res)

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


@app.route("/api/v1/db/read",methods=["POST"])
def read_db():
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
    app.run(host="0.0.0.0")
