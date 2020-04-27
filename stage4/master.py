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

def master_function(event):
    print(event)
    children = zk.get_children("/worker")
    print(" MASTER FUNCTION There are %s children with names %s" % (len(children), children))
    l=[]
    sl = zk.get_children("/worker/slave")
    for i in sl:
#        print("I" ,i)
        nm ="/worker/slave/"+i
        data, stat = zk.get(nm)
        data = data.decode("utf-8")
        ind = data.find('PID')
        pid = data[ind+5:len(data)+1]
        pid=int(pid)
        l.append(pid)
    l.sort()
    tokill=l[0]
    print("SLAVE PID",tokill)

zk = KazooClient(hosts='zoo:2181')
zk.start()

zk.delete("/worker/slave", recursive=True)
zk.delete("/worker", recursive=True)

cmd = "cat /proc/self/cgroup | grep 'docker' | sed 's/^.*\///' | tail -n1"
cid = subprocess.check_output(cmd,shell=True)
cid = cid.decode("utf-8")
cid=cid[0:len(cid)-1]
client2 = docker.APIClient()
pid = client2.inspect_container(cid)['State']['Pid']
print("---PID", pid)

zk.ensure_path("/worker")
if zk.exists("/worker/master"):
    print("Master exists")
else:
    data1 = "I am master CID : "+cid+" PID : "+str(pid)
    data1 = data1.encode()
    zk.create("/worker/master", data1)

children = zk.get("/worker/master", watch=master_function)

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///master_rideshare.db'
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
    channel.queue_declare(queue='sq',durable=True)
    message = body
    channel.basic_publish(exchange='', routing_key='sq', body=message, properties=pika.BasicProperties(delivery_mode=2,))
    print(" [x] Sent %r" % message)
     
channel.basic_consume(queue='wq', on_message_callback=callback_write)

print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()


