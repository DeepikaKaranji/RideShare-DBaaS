import pika
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
import json
import subprocess
import docker
import logging

from kazoo.client import KazooClient
from kazoo.client import KazooState
logging.basicConfig()

zk = KazooClient(hosts='zoo:2181',timeout=1.0)
zk.start(timeout=1)

def master_function(event):
    print(event)
    children = zk.get_children("/worker")
    #print(" MASTER FUNCTION There are %s children with names %s" % (len(children), children))
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
        #print(container)
        zk.delete("/worker/slave/slave"+str(min_pid), version=-1, recursive=False)
        children = zk.get_children("/worker")
        #print(" AFTER DELETING %s children with names %s" % (len(children), children))#slave
        children = zk.get_children("/worker/slave")
        print(" ALL SLAVES %s children with names %s" % (len(children), children))#slave1
        data1 = "I am master CID : "+min_cid+" PID : "+str(min_pid)
        data1 = data1.encode()
        zk.create("/worker/master", data1,ephemeral=True)
        children = zk.get_children("/worker")
        print(" AFTER CHANGING %s children with names %s" % (len(children), children))#master,slave
        print("SLAVE PID",min_pid)
        print("SLAVE CID",min_cid)
        children = zk.get("/worker/master", watch=master_function)
 
#zk.delete("/worker/slave", recursive=True)
#zk.delete("/worker", recursive=True)

cmd = "cat /proc/self/cgroup | grep 'docker' | sed 's/^.*\///' | tail -n1"
cid = subprocess.check_output(cmd,shell=True)
cid = cid.decode("utf-8")
cid=cid[0:12]
client2 = docker.APIClient()
pid = client2.inspect_container(cid)['State']['Pid']
print("---MASTER PID", pid)
print("---CID", cid)

zk.ensure_path("/worker")
if zk.exists("/worker/master"):
    print("Master exists")
else:
    data1 = "I am master CID : "+cid+" PID : "+str(pid)
    data1 = data1.encode()
    zk.create("/worker/master", data1,ephemeral = True)

children = zk.get("/worker/master", watch=master_function)

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+str(pid)+'.db'
db = SQLAlchemy(app)


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

db.create_all()
connection = pika.BlockingConnection(pika.ConnectionParameters(host='rmq'))
channel = connection.channel()


channel.queue_declare(queue='wq',durable = True)

def callback_write(ch, method, properties, body): 
    print(" [x] Received %r" % body)
    x=json.loads(body)
    data = x["insert"]
    cn = x["column"]
    tn = x["table"]
    tn=eval(tn) 
    new_user=tn()
    for i in range(len(data)):
        data1 = data[i]
        c1 = cn[i]
        setattr(new_user, c1, data1)
    db.session.add(new_user)
    db.session.commit()
        #print("DDDOOOOOOONNNNNNNNNNEEEEEEEEEEEEEEEEE")
    ch.basic_ack(delivery_tag = method.delivery_tag)
    #channel.queue_declare(queue='sq',durable=True)
    channel.exchange_declare(exchange='logs',
                         exchange_type='fanout')
    message = body
    channel.basic_publish(exchange='logs', routing_key='', body=message)
    print(" [x] Sent %r" % message)
     
channel.basic_consume(queue='wq', on_message_callback=callback_write)

print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()


