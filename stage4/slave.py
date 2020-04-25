import pika
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
import json
import docker
import subprocess

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///slave_rideshare.db'
db = SQLAlchemy(app)



import logging

from kazoo.client import KazooClient
from kazoo.client import KazooState
logging.basicConfig()

def demo_fuc(event):
    # Create a node with dat
    print(event)
    children = zk.get_children("/worker/slave")
    print(" IN DEMO There are %s children with names %s" % (len(children), children))


zk = KazooClient(hosts='zoo:2181')
zk.start()
cmd = "cat /proc/self/cgroup | grep 'docker' | sed 's/^.*\///' | tail -n1"
cid = subprocess.check_output(cmd,shell=True)
cid = cid.decode("utf-8")
cid=cid[0:len(cid)-1]
#cidout = cid[0:
client2 = docker.APIClient()
pid = client2.inspect_container(cid)['State']['Pid']
print("---PID", pid)

print('#########################')
#print(container)

print("------------------------")

#zk.ensure_path("/worker")
#zk.ensure_path("/worker/slave")

if zk.exists("/worker/slave"):
    print("Slave exists")
else:
    zk.create("/worker/slave", b"hi")

children = zk.get_children("/worker/slave", watch=demo_fuc)
print("SLAVESSSS OUTSIDE There are %s children with names %s" % (len(children), children))

if zk.exists("/worker/slave/slave"+str(pid)):
    print("Slave exists")
else:
    data1 = "I am slave CID : "+cid+" PID : "+str(pid)
    data1 = data1.encode()
    zk.create("/worker/slave/slave"+str(pid), data1)

#data, stat = zk.get_children("/worker/slave")
#print("Version: %s, data: %s" % (stat.version, data.decode("utf-8")))

#zk.delete("/producer/node_1")
print("Deleted /producer/node_1")

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
channel.queue_declare(queue='rpcq', durable = True)
channel.queue_declare(queue='sq',durable = True)

def callback_sync(ch, method, properties, body): 
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
     
#print(' [*] Waiting for messages. To exit press CTRL+C')
#channel.start_consuming()


def callback_read(x): 
    print(" [x] Received IN READ%r" % x)
#    x=json.loads(body)
    data = x["where"]
    cn = x["column"]
    tn = x["table"]
    print(data,cn,tn)
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
        #user1= tn.query.filter((x1 == v1)&(x2 == v2)).all()
        user1= tn.query.filter(x1 == v1).filter(x2 == v2).all()
        #print user1
        d = {}
        for i in user1:	
            cnt = 0
            for j in cn:
                if j not in d:
                    d[j] =[]
                    cnt =cnt+1
                a = getattr(i, j)
                d[j].append(a)
#    print(d)
    return d
    #print("DDDDDDDDDDDOOOOOOOOOOOOOOOOOONNNNNNNNNNNNNNEEEEEEEEEEEEEEEEEEEE")
    ch.basic_ack(delivery_tag = method.delivery_tag) 
    

def on_request(ch, method, props, body):
    #n = int(body)
    print(" [x] Received IN REQUEST %r" % body)
    x=json.loads(body)
    #print(" [.] fib(%s)" % n)
    response = callback_read(x)

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=str(response))
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(queue='sq', on_message_callback=callback_sync)
channel.basic_consume(queue='rpcq', on_message_callback=on_request)
print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming() 

