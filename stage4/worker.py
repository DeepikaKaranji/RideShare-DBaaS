import pika
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
import json
import os

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rideshare.db'
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

channel.queue_declare(queue='test1')


def callback(ch, method, properties, body): 
    print(" [x] Received %r" % body)
    print("-----------")
    a=os.getpid()
    print(a)
    print("-----------")
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


channel.basic_consume(queue='test1', on_message_callback=callback)

print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()
