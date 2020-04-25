from flask import Flask, jsonify, request, abort, make_response
from flask_sqlalchemy import SQLAlchemy
import json

import uuid
import pika

print("HI ORCH")

app = Flask(__name__)

connection = pika.BlockingConnection(pika.ConnectionParameters(host='rmq'))
channel = connection.channel()
channel.queue_declare(queue='wq',durable = True)
    

@app.route("/api/v1/db/write",methods=["POST"])
def write_db():
    data = request.get_json()["insert"]
    cn = request.get_json()["column"]
    tn = request.get_json()["table"]
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
    return {},200

corr_id = str(uuid.uuid4())


class TestRpcClient(object):

    def __init__(self):
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
    test= "{\"where\": "+"\"" + data + "\"" + ", \"table\"" +":"+ "\"" + tn + "\"" + ",\"column\" : [ "
    for i in range(0,len(cn)-1):
    	test= test+ "\"" +cn[i] + "\"" + ","
    test= test + "\"" + cn[len(cn)-1] + "\" ] }"
    print(" [x] Sent %r" % test)
    test_rpc = TestRpcClient()
    result = test_rpc.call(test)
    print("RPC is %r" %result)
    return {},200

connection.close()

if __name__ == "__main__":
    app.debug=True
    app.run(host="0.0.0.0")
