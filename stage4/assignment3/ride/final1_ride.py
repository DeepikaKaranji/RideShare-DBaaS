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


# with open('./config.json') as config_file:
#     config = json.load(config_file)

# port = config["ride_port"]
# server = config["ride_ip"] + ":" + port
# userMicroService = config["user_ip"] + ":" + config["user_port"]
app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ride_db.db'
db = SQLAlchemy(app)
# app.logger.info("USER MICROSERVICE", userMicroService)


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


############################################### CUSTOM delete microservice###################################################
@app.route("/api/v1/rides/custom",methods=["GET"])
def delete_microservice_ride():
    print("---------------- Custom delete ----------------")
    c = app.test_client()

    if 'username' in request.args:
        user=str(request.args['username'])


#    user = request.get_json()['user']
    print("RECEIVED USERNAME -------", user)

    para1 = {
    "table"  : "ride_details",
	"column" : ["username"],
	"where" :  "username = "+ user
    }
    # print "PARA 1 --------", para1
    #response = c.post('/api/v1/db/read',json=para1,follow_redirects=True)
    url = 'http://52.203.199.62:5000/api/v1/db/read'
    response = requests.post(url, data = para1)
    if(response.get_json()): 
        ride_details.query.filter(ride_details.username == user).delete()
        db.session.commit()
    else:
        return make_response("Username doesnt exist \
            in ride_details table",400)
    return make_response("{}",200)


########################### COUNT RIDES ########################################
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
        url = 'http://52.203.199.62:5000/api/v1/db/read'
        response = requests.post(url, json = para6)
        response = response.text
        ride= response.encode("ascii", "ignore")
        print("RESPONSE COUNT",ride)
        #ride= ride_details.query.filter(ride_details.rideid).count()
        cnt.append(ride)
        return make_response(json.dumps(cnt), 200)
    # return jsonify(count)
    else:
        count=count+1
        return make_response("405,Method Not Allowed",405)

###############################################TASK 3&4[CREATE RIDE and GET UPCOMING RIDES]################################################

@app.route("/api/v1/rides",methods=meth)
def add_ride():
    global count
    global rid
    if(request.method=="POST"):
        count=count+1
        # print "-----------ride api 3-----------"
        un = request.get_json()["created_by"]
        ts = request.get_json()["timestamp"]
        src =int(request.get_json()["source"])
        dest =int( request.get_json()["destination"])
        c = app.test_client()
        
        # resp0 = requests.get('http://127.0.0.1:5000/users/api/v1/users')
        
        #resp0 = requests.get('http://171.19.0.2:80/api/v1/users')
        headers = {'Origin': '54.173.81.6'}
        resp0 = requests.get('http://hopelb-1353512799.us-east-1.elb.amazonaws.com/api/v1/users', headers = headers)
        resp0 = resp0.json()
        print("resp0------------------", un in resp0)
        if(resp0 and un in resp0):
            rid = randint(0,9999)
            if((src>0)and(src<199)):
                if((dest>0)and(dest<199)):
                    #c = app.test_client()
                    para2 = {
                            "table"  : "ride_details",
                            "column" : ["rideid","username","timestamp","source","destination"],
                            "insert" : [rid,un,ts,src,dest]
                    }
                    #resp2 = c.post('/api/v1/db/write',json=para2,follow_redirects=True)
                    url = 'http://52.203.199.62:5000/api/v1/db/write'
                    resp2 = requests.post(url, json = para2)
                    print("WRITE DONEEEEE", resp2)
                    para3 = { "table": "ride_details",
                        "column":["rideid"],
                        "where":"username = "+un
                    }
                    
                    #resp3 = c.post('/api/v1/db/read',json=para3,follow_redirects=True)
                    url = 'http://52.203.199.62:5000/api/v1/db/read'
                    resp3 = requests.post(url,json = para3)
                    resp3 = resp3.text
                    resp3= resp3.encode("ascii", "ignore")
                    obj = json.dumps(resp3)
                    #print("OBJJJJJJJJ------", obj, type(obj))
                    #global rid
                    # print "-----------", obj
                    for elem in obj["rideid"]:
                        #global rid
                        rid=rid+1
                        
                        para4 = {
                            "table" :"join_user",
                            "column" : ["srn","rideid","username"],
                            "insert"  : [rid,elem, un]
                        }
                       # resp2 = c.post('/api/v1/db/write',json=para4,follow_redirects=True)
                        url = 'http://52.203.199.62:5000/api/v1/db/write'
                        resp2 = requests.post(url, json = para4)
                else:
                    return make_response("Destination does not exist", 400)
            else:
                return make_response("Source doesnot exist", 400)
        else:
            return make_response("Username doesnot exist", 400)
        return make_response( "{}",201)
    if(request.method=="GET"):
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
        
        c = app.test_client()
        para1 = {
        "table"  : "ride_details",
        "column" : ["rideid","username","timestamp"],
        "where" :  "source = "+ src+" AND destination = "+dest
        }
        #response = c.post('/api/v1/db/read',json=para1,follow_redirects=True)
        url = 'http://52.203.199.62:5000/api/v1/db/read'
        response = requsts.post(url, data = para1)

        obj = response.get_json()
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
            return make_response("Ride Id does not exist", 400)    
    
    else:
        count=count+1
        return make_response("405,Method Not Allowed",405)

###############################################TASK 5,6,7[RIDE DETAILS,]################################################
@app.route('/api/v1/rides/<int:task_id>', methods=meth)
def get_task(task_id):             
    global count
    if(request.method=="GET"):    
        count=count+1
        c = app.test_client()
        # ride= ride_details.query.filter_by(rideid = task_id).first()
        para1 = {
        "table"  : "ride_details",
        "column" : ["rideid","username","timestamp","source","destination"],
        "where" :  "rideid = "+ str(task_id)
        }
        #resp1= c.post('/api/v1/db/read',json=para1,follow_redirects=True)
        url = 'http://52.203.199.62:5000/api/v1/db/read'
        resp1 = requests.post(url, data = para1)
        ride_obj = resp1.get_json()
    #    print "~~~~~~~~~", ride_obj

        ride_dict = {}
        for key in ride_obj:
            ride_dict[key] = ride_obj[key][0]

        # ride1= join_user.query.filter(join_user.rideid == task_id).all()
        para2 = {
        "table"  : "join_user",
        "column" : ["rideid","username"],
        "where" :  "rideid = "+ str(task_id)
        }

#        resp2 = c.post('/api/v1/db/read',json=para2,follow_redirects=True)
        url = 'http://52.203.199.62:5000/api/v1/db/read'
        resp2 = requests.post(url, data = para2)
        ride1_obj = resp2.get_json()
    #    print "---------", ride1_obj
    
      #  res= ride1_obj["username"]
        if(not ride_obj):
            return make_response("Ride id does not exist",400)
        else:
            res= ride1_obj["username"]
            return make_response(jsonify({"rideid":ride_dict["rideid"],"created By":ride_dict["username"],\
                "users":res,"timestamp":ride_dict["timestamp"],"source":ride_dict["source"],\
                    "destination":ride_dict["destination"]}),200)
        #    return make_response("ok", 200)
    if(request.method=="POST"):
        count=count+1
        un = request.get_json()["username"]

        c = app.test_client()
        # user1= user_details.query.filter_by(username = un).first()
        headers = {'Origin': '54.173.81.6'}
        resp1 = requests.get('http://hopelb-1353512799.us-east-1.elb.amazonaws.com/api/v1/users', headers = headers)
        user1_obj = resp1.json()

        # rideid1=ride_details.query.filter_by(rideid =task_id).first()
        para2 = {
        "table"  : "ride_details",
        "column" : ["username"],
        "where" :  "rideid = "+ str(task_id)
        }
        #resp2= c.post('/api/v1/db/read',json=para2,follow_redirects=True)
        url = 'http://52.203.199.62:5000/api/v1/db/read'
        resp2 = requests.post(url, data = para2)
        rideid1_obj = resp2.get_json()
        if(user1_obj and un in user1_obj): 
            if(rideid1_obj):
                global rid
                rid=rid+1
                para3 = {
                    "table"  : "join_user",
                    "column" : ["srn","rideid","username"],
                    "insert" : [rid,task_id,un]
                }
                #resp2= c.post('/api/v1/db/write',json=para3,follow_redirects=True)
                url = 'http://52.203.199.62:5000/api/v1/db/write'
                resp2 = requests.post(url, data = para3)
                return make_response("OK",200)

                # ride1=join_user(srn =rid,rideid = task_id, username = un)
                # db.session.add(ride1)
                # db.session.commit()
            else:
                return make_response("rideid does not exist",400)
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
#        response = c.post('/api/v1/db/read',json=para1,follow_redirects=True
        url = 'http://52.203.199.62:5000/api/v1/db/read'
        response = requests.post(url, data = para1)

        if(response.get_json()): 
            ride_details.query.filter(ride_details.rideid == str(task_id)).delete() 
            db.session.commit()
        else:
            return make_response("Ride ID does not exist",400)
        return make_response("{}",200)
    else:
        count=count+1
        return make_response("405,Method Not Allowed",405)


####################################  CLEAR DB #########################
@app.route("/api/v1/db/clear",methods=meth)
def delete():
    global count
    if(request.method=="POST"):
        count=count+1
        srn = randint(0,9999)
        signal = {
        "table" : "signal_table",
        "column" : ["srn","cleardb_flag"],
        "insert" : [str(srn),"1"]
        }
        url = 'http://52.203.199.62/api/v1/db/read'
        res = requests.post(url, data = signal)
        return {},200
    else:
        count=count+1
        return make_response("405,Method Not Allowed",405)
        
#ride_details.query.delete()

# @app.route("/api/v1/db/read",methods=["POST"])
# def read_db():
#     print("####9####")
#     # print type(request)

#     data = request.get_json()["where"]
#     cn = request.get_json()["column"]
#     tn = request.get_json()["table"]
#     print(tn)



#     # info = request.get_json() #unicode
#     # info = json.dumps(info) #string
#     # info = eval(info)
#     # print type(info) #string
#     # print "---------------------"

#     # info = ast.literal_eval(info) 
#     # print type(info) #dict
#     # print "###################", info

#     # data = info["where"]
#     # print "---DATA---", data
#     # # print "^^^^^^^", info["where"]
#     # # print "&&&&&&&", info
#     # cn = info["column"]
#     # print("---CN---", cn)

#     # tn = info["table"]
#     # # tn=eval(tn)
#     # print("---TN---", tn) 

#     # print "TN TYPE", type(tn) #str
#     # tn = json.loads(tn)
#     # tn=jsonify(tn)
#     print "TN ON EVAL TYPE----", type(tn)
#     # new_user=tn()

#     # try:
#     #     with sqlite3.connect("ride_db.db") as con:
#     #         cur = con.cursor()
#     #         ind = data.find('=')
#     #         att = data[:ind-1]
#     #         val = data[ind+2:]

#     #         query =  
#     #         cur.execute("SELECT "+cn +\
#     #                 "FROM "+tn+"WHERE "+ )
#     #             con.commit()
#     # except:
#     #     abort(500)




#     data = str(data)
#     result = data.find('AND') 
#     if(result==-1):
#         ind = data.find('=')
#         att = data[:ind-1]
#         val = data[ind+2:]
#         x = getattr(tn, att)
#         user1= tn.query.filter((x == val)).all()
#         d = {}
#         for i in user1:
#             cnt = 0
#             for j in cn:
#                 if j not in d:
#                     d[j] =[]
#                     cnt =cnt+1
#                 a = getattr(i, j)
#                 d[j].append(a)
#         return jsonify(d)
#         return {}

#     else:
#         q1 = data[:result-1]
#         q2 = data[result+4:]
#         i1 = q1.find('=')
#         a1 = q1[:i1-1]
#         v1 = q1[i1+2:]
#         x1 = getattr(tn, a1)
#         i2 = q1.find('=')
#         a2 = q1[:i2-1]
#         v2 = q1[i2+2:]
#         x2 = getattr(tn, a2)
#         user1= tn.query.filter((x1 == v1)&(x2 == v2)).all()
#         d = {}
#         for i in user1:
#             cnt = 0
#             for j in cn:
#                 if j not in d:
#                     d[j] =[]
#                     cnt =cnt+1
#                 a = getattr(i, j)
#                 d[j].append(a)
#         return jsonify(d)
#         return {}


if __name__ == "__main__":
    app.debug=True
    app.run(host='0.0.0.0',port='80')
#    app.run()
