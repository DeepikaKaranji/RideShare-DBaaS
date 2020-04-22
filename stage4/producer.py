from flask import Flask, jsonify, request, abort, make_response
from flask_sqlalchemy import SQLAlchemy
import json


import pika

connection = pika.BlockingConnection(pika.ConnectionParameters(host='rmq'))
channel = connection.channel()

channel.queue_declare(queue='task_queue',durable=True)

message = " Hello world "

channel.basic_publish(exchange='', routing_key='task_queue', body=message, properties=pika.BasicProperties(delivery_mode=2,))
print(" [x] Sent %r" % message)
connection.close()
