from flask import Flask, jsonify, request, abort, make_response
from flask_sqlalchemy import SQLAlchemy
from random import randint
from datetime import datetime
from datetime import date
import time
import json
import sqlite3 as sqlite3
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user_db.db'
db = SQLAlchemy(app)

count = 0
final=[]
meth = ["VIEW", "GET","PUT","POST","DELETE","HEAD","OPTIONS","PATCH","CONNECT","PURGE","LOCK","LINK","UNLINK","UNLOCK","COPY","PROPFIND"]
######################################## HTTP set reset count ######################################
@app.route("/api/v1/_count", methods=["GET", "DELETE"])
def get_http_count():
        print("HTTP count api")
        global count
        if(request.method=="GET"):
 	    global final
	    final=[]
            final.append(count)
            return json.dumps(final)
        else:
            count-=count
            return make_response(jsonify({}), 200)


###############################################TASK 0 & 1 [BOTH LIST AND CREATE USER]################################################

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d.values()

@app.route("/api/v1/users",methods=meth)
def list_users():
    global count
    if(request.method=="GET"):
        print("*******GET METHOD LIST USR************", request.headers)
        print("---------------user list api------------")
        count=count+1
        # a = user_details.query.filter(user_details.username).all()

        para0 =  {
        "table"  : "user_details",
	    "column" : ["password","username"],
        "where"  : "fetchall"
        }
        url = 'http://52.203.199.62:80/api/v1/db/read'
        response = requests.post(url, json = para0)
        print("*******RESPONSE",response)
        print("**********, TYPE OF RESPONSE", type(response))
        all = response.json()
        print("*********** ALL", all)
        print("********** TYPE OF ALL", type(all))

        return make_response(json.dumps(all), 200)

    if(request.method=="PUT"):
        cps =['1','0','2','3','4','5','6','7','8','9','a','b','c','d','e','f','A','B','C','D','E','F']
        # print(" ------------------- create user api -------------------")
        count=count+1
        un = request.get_json()["username"]
        ps = request.get_json()["password"]
        c = app.test_client()
        para1 = {
        "table"  : "user_details",
        "column" : ["username","password"],
        "where" :  "username = "+ un
        }
        
        # response = c.post('/api/v1/db/read',json=para1,follow_redirects=True,\
        #      environ_base={'REMOTE_ADDR': '127.0.0.1'})
        # response = c.post('/api/v1/db/read',json=para1,follow_redirects=True)
        url = 'http://52.203.199.62:80/api/v1/db/read'
        response = requests.post(url, json = para1)
        print("......response.........",json.dumps(response.json()))
        print("......response testing.........",response.json())
        print("..............................................",len(response.json()))

        if(json.dumps(response.json())!='{}'): 
            return make_response("Key exists",400)
        if len(ps)!=40:
            #return jsonify("Password is not of type SHA1 hash hex"),400
            return make_response("Password not SHA1",400)
            
        else:
            for i in ps:
                if(i not in cps):
                # return jsonify("Password is not of type SHA1 hash hex"),400
                    return make_response("Password not SHA1",400)
        c = app.test_client()
        para = {
        "table"  : "user_details",
        "column" : ["username","password"],
        "insert" : [un,ps]
        }
        # response = c.post('/api/v1/db/write',json=para,follow_redirects=True)
        url = 'http://52.203.199.62:80/api/v1/db/write'
        response = requests.post(url, json = para)

        return make_response("{}", 201)
    else:
        count=count+1
        return make_response("405,Method Not Allowed",405)

###############################################TASK 2################################################

@app.route("/api/v1/users/<user>",methods=meth)
def delete_user(user):
    global count
    if(request.method=="DELETE"):
        #print(" ------------------- delete user api --------------------")
        count=count+1
        c = app.test_client()
        para1 = {
        "table"  : "user_details",
        "column" : ["username", "password"],
        "where" :  "username = "+ user
        }
        # response = c.post('/api/v1/db/read',json=para1,follow_redirects=True)
        url = 'http://52.203.199.62:80/api/v1/db/read'
        response = requests.post(url, json = para1)
        res = response.text
        res = res.encode("ascii","ignore")
        print("----------RESPONSE-------", res)
       # print("------responsedump---------", json.dumps(response.json()))

        #user1= user_details.query.filter_by(username = user).first()
        if(res!='{}'): 
            #res1 = user_details.query.filter(user_details.username == user).delete()
            #db.session.commit()
            #payload = {"user":user}
            #print("PAYLOAD--------------- ", payload)
            para6 = {
            "table" : "user_details",
            "column" : "DELETE",
            "insert" : "username = " + user

            }
            url = 'http://52.203.199.62:80/api/v1/db/write'
            response = requests.post(url, json = para6)
            print("THIS SHOULDNT BE COMMENTED!!!")
            #url = 'http://hopeLB-598791841.us-east-1.elb.amazonaws.com/api/v1/rides/custom?username='+user
            #res2 = requests.get(url)
    #       res2 = requests.post('http://hopeLB-598791841.us-east-1.elb.amazonaws.com/api/v1/rides/custom', params = payload)
            db.session.commit()
            return make_response("{}",200)
            #if(res1):
             #   return make_response("{}",200) 
        else:
            return make_response("Username does not exist",400)
    else:
        count=count+1
        return make_response("405,Method Not Allowed",405)


########################### CLEAR DB ############################
@app.route("/api/v1/db/clear",methods=meth)
def delete():
    global count
    if(request.method=="POST"):
        count=count+1
        print("IN CLEAR DB USER")
        srn = randint(0,9999)
        signal = {
        "table" : "user_details",
        "column" :"CLEARDB",
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
    app.run(host='0.0.0.0', port = '80')
    #app.run()
