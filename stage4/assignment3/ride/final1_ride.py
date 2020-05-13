from flask import Flask, jsonify, request, abort, make_response
from flask_sqlalchemy import SQLAlchemy
from random import randint
from datetime import datetime
from datetime import date
import time
import json
import requests
import ast
import sqlite3 as sqlite3

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ride_db.db'
db = SQLAlchemy(app)

rid = 1
count = 0
meth = ["VIEW", "GET","PUT","POST","DELETE","HEAD","OPTIONS","PATCH","CONNECT","PURGE","LOCK","LINK","UNLINK","UNLOCK","COPY","PROPFIND"]


######################################## HTTP set reset count ######################################
@app.route("/api/v1/_count", methods=["GET", "DELETE"])
def get_http_count():
        global count
        print("HTTP count api")
        if(request.method=="GET"):
            final=[]
            final.append(count)
            return json.dumps(final)
        else:
            count-=count
            return make_response(jsonify({}), 200)


############################################### CUSTOM DELETE MICROSERVICE ###################################################
@app.route("/api/v1/rides/custom",methods=["GET"])
def delete_microservice_ride():
    c = app.test_client()

    if 'username' in request.args:
        user=str(request.args['username'])
    para1 = {
    "table"  : "ride_details",
	"column" : ["username"],
	"where" :  "username = "+ user
    }
    url = 'http://52.203.199.62:80/api/v1/db/read'
    response = requests.post(url, data = para1)
    if(response.get_json()): 
        ride_details.query.filter(ride_details.username == user).delete()
        db.session.commit()
    else:
        return make_response("Username doesnt exist \
            in ride_details table",400)
    return make_response("{}",200)


################################ COUNT RIDES ########################################
@app.route('/api/v1/rides/count', methods=meth)
def get_count():
    if(request.method=="GET"):
        global count 
        count =count+1
        cnt=[]
        para6 = {
            "table" : "COUNT",
            "column" : "COUNT",
            "where" : "count_ride"

        }
        url = 'http://52.203.199.62:80/api/v1/db/read'
        response = requests.post(url, json = para6)
        response = response.text
        ride= response.encode("ascii", "ignore")
        print("RESPONSE COUNT",ride)
        cnt.append(ride)
        return make_response(json.dumps(cnt), 200)
    else:
        count=count+1
        return make_response("405,Method Not Allowed",405)

###############################################TASK 3&4[CREATE RIDE and GET UPCOMING RIDES]################################################

@app.route("/api/v1/rides",methods=meth)
def add_ride():
    global count
    global rid
    if(request.method=="POST"):
        # create ride
        count=count+1
        un = request.get_json()["created_by"]
        ts = request.get_json()["timestamp"]
        src =int(request.get_json()["source"])
        dest =int( request.get_json()["destination"])
        c = app.test_client()
        # get list of users
        headers = {'Origin': '52.2.156.61'}
        resp0 = requests.get('http://hopelb-1353512799.us-east-1.elb.amazonaws.com/api/v1/users', headers = headers)
        resp0 = resp0.text
        # if user exists, create ride
        if(resp0 and un in resp0):
            rid = randint(0,9999)
            if((src>0)and(src<199)):
                if((dest>0)and(dest<199)):
                    para2 = {
                            "table"  : "ride_details",
                            "column" : ["rideid","username","timestamp","source","destination"],
                            "insert" : [str(rid),un,ts,str(src),str(dest)]
                    }
                    url = 'http://52.203.199.62:80/api/v1/db/write'
                    resp2 = requests.post(url, json = para2)
                    para3 = { "table": "ride_details",
                        "column":["rideid"],
                        "where":"username = "+un
                    }
                    
                    url = 'http://52.203.199.62:80/api/v1/db/read'
                    resp3 = requests.post(url,json = para3)
                    resp3 = resp3.text
                    resp3= resp3.encode("ascii", "ignore")
                    obj = eval(resp3)
                    
                    for elem in obj["rideid"]:
                        rid=rid+1
                        para4 = {
                            "table" :"join_user",
                            "column" : ["srn","rideid","username"],
                            "insert"  : [str(rid),str(elem), un]
                        }
                        url = 'http://52.203.199.62:80/api/v1/db/write'
                        resp2 = requests.post(url, json = para4)
                        print("AFTER JOIN USER RESP",resp2)
                else:
                    return make_response("Destination does not exist", 400)
            else:
                return make_response("Source doesnot exist", 400)
        else:
            return make_response("Username doesnot exist", 400)
        return make_response( "{}",201)

    if(request.method=="GET"):
        # get upcoming ride
        count=count+1
        results={}
        res=[]
        final=[]
        if 'source' in request.args:
            src=str(request.args['source'])
        if 'destination' in request.args:    
            dest=str(request.args['destination'])
        else:
            return make_response("Please mention source and destination",400)
        curr_time=datetime.now().strftime("%d-%m-%Y:%S-%M-%H")

        para1 = {
        "table"  : "ride_details",
        "column" : ["rideid","username","timestamp"],
        "where" :  "source = "+ src+" AND destination = "+dest
        }
        # get ride details for given source and destination
        url = 'http://52.203.199.62:80/api/v1/db/read'
        response = requests.post(url, json = para1)

        obj = response.text
        obj = obj.encode("ascii","ignore")
        obj= eval(obj)
        if(obj): 
            i = 0
            for i in range(len(obj['username'])):
                results = {}
                for key in obj:
                    results[key] = obj[key][i]
                res.append(results)
            for record in res:
                tdelta= datetime.strptime(record['timestamp'],'%d-%m-%Y:%S-%M-%H')\
                    - datetime.strptime(curr_time,'%d-%m-%Y:%S-%M-%H')
                if(tdelta.days >-1 and tdelta.seconds>0):
                    final.append(record)
            return json.dumps(final)
        else:
            return make_response("Ride does not exist", 204)    
    
    else:
        count=count+1
        return make_response("405,Method Not Allowed",405)

###############################################TASK 5,6,7[RIDE DETAILS,]################################################
@app.route('/api/v1/rides/<int:task_id>', methods=meth)
def get_task(task_id):             
    global count
    if(request.method=="GET"):
        # get details of given ride
        count=count+1
        c = app.test_client()
        para1 = {
        "table"  : "ride_details",
        "column" : ["rideid","username","timestamp","source","destination"],
        "where" :  "rideid = "+ str(task_id)
        }
        url = 'http://52.203.199.62:80/api/v1/db/read'
        resp1 = requests.post(url, json  = para1)
        ride_obj = resp1.text
        ride_obj = ride_obj.encode("ascii","ignore")
        ride_obj = eval(ride_obj)
        ride_dict = {}
        for key in ride_obj:
            ride_dict[key] = ride_obj[key][0]

        para2 = {
        "table"  : "join_user",
        "column" : ["rideid","username"],
        "where" :  "rideid = "+ str(task_id)
        }

        url = 'http://52.203.199.62:80/api/v1/db/read'
        resp2 = requests.post(url, json = para2)
        ride1_obj = resp2.text
        ride1_obj = ride1_obj.encode("ascii","ignore")
        ride1_obj = eval(ride1_obj)
    
        if(not ride_obj):
            return make_response("Ride id does not exist",204)
        else:
            res= ride1_obj["username"]
            return make_response(jsonify({"rideid":ride_dict["rideid"],"created By":ride_dict["username"],\
                "users":res,"timestamp":ride_dict["timestamp"],"source":ride_dict["source"],\
                    "destination":ride_dict["destination"]}),200)

    if(request.method=="POST"):
        count=count+1
        un = request.get_json()["username"]

        c = app.test_client()
        headers = {'Origin': '52.2.156.61'}
        resp1 = requests.get('http://hopelb-1353512799.us-east-1.elb.amazonaws.com/api/v1/users', headers = headers)
        user1_obj = resp1.json()

        para2 = {
        "table"  : "ride_details",
        "column" : ["username"],
        "where" :  "rideid = "+ str(task_id)
        }

        url = 'http://52.203.199.62:80/api/v1/db/read'
        resp2 = requests.post(url, json = para2)
        rideid1_obj = resp2.text
        rideid1_obj = rideid1_obj.encode("ascii","ignore")
        rideid1_obj = eval(rideid1_obj)
        if(user1_obj and un in user1_obj): 
            if(rideid1_obj):
                global rid
                rid=rid+1
                para3 = {
                    "table"  : "join_user",
                    "column" : ["srn","rideid","username"],
                    "insert" : [str(rid),str(task_id),un]
                }
                url = 'http://52.203.199.62:80/api/v1/db/write'
                resp2 = requests.post(url, json = para3)
                return make_response("OK",200)

            else:
                return make_response("rideid does not exist",204)
        else:
            return make_response("Username does not exist", 400) 
    if(request.method=="DELETE"):
        count=count+1
        c = app.test_client()
        para1 = {
        "table"  : "ride_details",
        "column" : ["rideid"],
        "where" :  "rideid = "+ str(task_id)
        }
        url = 'http://52.203.199.62:80/api/v1/db/read'
        response = requests.post(url, json = para1)
        res = response.text
        res = res.encode("ascii","ignore")
        
        if(res!='{}'):
            para6 = {
            "table" : "ride_details",
            "column" : "DELETE",
            "insert" : "rideid = " + str(task_id)

            }
            url = 'http://52.203.199.62:80/api/v1/db/write'
            response = requests.post(url, json = para6)
            db.session.commit()
        else:
            return make_response("Ride ID does not exist",204)
        return make_response("{}",200)
    else:
        count=count+1
        return make_response("405,Method Not Allowed",405)


####################################  CLEAR DB  ###################################
@app.route("/api/v1/db/clear",methods=meth)
def delete():
    global count
    if(request.method=="POST"):
        count=count+1
        srn = randint(0,9999)
        signal = {
        "table" : "ride_details",
        "column" : "CLEARDB",
        "insert" : [str(srn),"1"]
        }
        url = 'http://52.203.199.62:80/api/v1/db/write'
        res = requests.post(url, json = signal)
        return make_response("{}",200)
    else:
        count=count+1
        return make_response("405,Method Not Allowed",405)
        
if __name__ == "__main__":
    app.debug=True
    app.run(host='0.0.0.0',port='80')
