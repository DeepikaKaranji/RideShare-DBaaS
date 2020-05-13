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
######################################## HTTP SET RESET COUNT ######################################
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

###############################################TASK 0 & 1 [LIST AND CREATE USER]################################################

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d.values()

@app.route("/api/v1/users",methods=meth)
def list_users():
    global count
    if(request.method=="GET"):
        # list users
        count=count+1
        para0 =  {
        "table"  : "user_details",
	    "column" : ["password","username"],
        "where"  : "fetchall"
        }
        url = 'http://52.203.199.62:80/api/v1/db/read'
        response = requests.post(url, json = para0)
        all = response.json()
        return make_response(json.dumps(all), 200)

    if(request.method=="PUT"):
        # create user
        cps =['1','0','2','3','4','5','6','7','8','9','a','b','c','d','e','f','A','B','C','D','E','F']
        count=count+1
        un = request.get_json()["username"]
        ps = request.get_json()["password"]
        c = app.test_client()
        para1 = {
        "table"  : "user_details",
        "column" : ["username","password"],
        "where" :  "username = "+ un
        }
        
        url = 'http://52.203.199.62:80/api/v1/db/read'
        response = requests.post(url, json = para1)
        
        if(json.dumps(response.json())!='{}'): 
            return make_response("Key exists",400)
        if len(ps)!=40:
            return make_response("Password not SHA1",400)
        else:
            for i in ps:
                if(i not in cps):
                    return make_response("Password not SHA1",400)
        c = app.test_client()
        para = {
        "table"  : "user_details",
        "column" : ["username","password"],
        "insert" : [un,ps]
        }
        url = 'http://52.203.199.62:80/api/v1/db/write'
        response = requests.post(url, json = para)

        return make_response("{}", 201)
    else:
        count=count+1
        return make_response("405,Method Not Allowed",405)

###############################################TASK 2 [DELETE USER] ################################################

@app.route("/api/v1/users/<user>",methods=meth)
def delete_user(user):
    global count
    if(request.method=="DELETE"):
        # delete user
        count=count+1
        c = app.test_client()
        para1 = {
        "table"  : "user_details",
        "column" : ["username", "password"],
        "where" :  "username = "+ user
        }
        url = 'http://52.203.199.62:80/api/v1/db/read'
        response = requests.post(url, json = para1)
        res = response.text
        res = res.encode("ascii","ignore")

        if(res!='{}'): 
            
            para6 = {
            "table" : "user_details",
            "column" : "DELETE",
            "insert" : "username = " + user

            }
            url = 'http://52.203.199.62:80/api/v1/db/write'
            response = requests.post(url, json = para6)
            print("THIS SHOULDNT BE COMMENTED!!!")
            db.session.commit()
            return make_response("{}",200)
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
