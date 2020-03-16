from flask import Flask, jsonify, request, abort, make_response
from flask_sqlalchemy import SQLAlchemy
from random import randint
from datetime import datetime
from datetime import date
import time
import json
import sqlite3 as sqlite3
import requests
app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user_db.db'
db = SQLAlchemy(app)


class user_details(db.Model):
    username = db.Column(db.String(80), primary_key=True)
    password = db.Column(db.String(80))

class join_user(db.Model):
    srn= db.Column(db.Integer,primary_key=True)
    rideid = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80),primary_key=True)

db.create_all()

count = 0
final=[]
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
###############################################TASK 0################################################

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d.values()

@app.route("/api/v1/users",methods=["GET"])
def list_users():
    print("*******************", request.headers)
    print("---------------user list api------------")
    global count
    count=count+1
    # a = user_details.query.filter(user_details.username).all()
    conn = sqlite3.connect('user_db.db')
    conn.row_factory = dict_factory
    cur = conn.cursor()
    all = cur.execute("SELECT username FROM user_details;").fetchall()
    flatList = [ item for elem in all for item in elem]
    print "lenght mofo ----------------", len(flatList)
    return make_response(jsonify(flatList), 200)

###############################################TASK 1################################################

cps =['1','0','2','3','4','5','6','7','8','9','a','b','c','d','e','f','A','B','C','D','E','F']

@app.route("/api/v1/users",methods=["PUT"])
def add_user():
    print(" ------------------- create user api -------------------")
    global count
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
    response = c.post('/api/v1/db/read',json=para1,follow_redirects=True)
    if(response.get_json()): 
        return "Key exists",400
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
    response = c.post('/api/v1/db/write',json=para,follow_redirects=True)
    return make_response("{}", 201)

###############################################TASK 2################################################

@app.route("/api/v1/users/<user>",methods=["DELETE"])
def delete_user(user):
    print(" ------------------- delete user api --------------------")
    global count
    count=count+1
    c = app.test_client()
    para1 = {
    "table"  : "user_details",
	"column" : ["username"],
	"where" :  "username = "+ user
    }
    response = c.post('/api/v1/db/read',json=para1,follow_redirects=True)
    #user1= user_details.query.filter_by(username = user).first()
    if(response.get_json()): 
        res1 = user_details.query.filter(user_details.username == user).delete()
        db.session.commit()
        payload = {"user":user}
        print("PAYLOAD--------------- ", payload)
        url = 'http://hopeLB-598791841.us-east-1.elb.amazonaws.com/api/v1/rides/custom?username='+user
        res2 = requests.get(url)
#        res2 = requests.post('http://hopeLB-598791841.us-east-1.elb.amazonaws.com/api/v1/rides/custom', params = payload)
        db.session.commit()

        if(res1):
            return make_response("{}",200) 
    else:
        return make_response("Username does not exist",400)

###############################################TASK 8################################################

@app.route("/api/v1/db/write",methods=["POST"])
def write_db():
    data = request.get_json()["insert"]
    cn = request.get_json()["column"]
    tn = request.get_json()["table"]
    tn=eval(tn) 
    new_user=tn()
    for i in range(len(data)):
        data1 = data[i]
        c1 = cn[i]
        setattr(new_user, c1, data1)
    db.session.add(new_user)
    db.session.commit()
    return {},200

###############################################TASK 9################################################
    
@app.route("/api/v1/db/read",methods=["POST"])
def read_db():
    print "-------------- user api 9 ---------------------"
    data = request.get_json()["where"]
    cn = request.get_json()["column"]
    tn = request.get_json()["table"]
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
        return jsonify(d)
        return {}

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
        print user1
        d = {}
        for i in user1:
            cnt = 0
            for j in cn:
                if j not in d:
                    d[j] =[]
                    cnt =cnt+1
                a = getattr(i, j)
                d[j].append(a)
        return jsonify(d)
        return {}

########################### CLEAR DB ############################
@app.route("/api/v1/db/clear",methods=["POST"])
def delete():
    global count
    count=count+1
    user_details.query.delete()
    db.session.commit()
    return {},200

if __name__ == "__main__":
    app.debug=True
    app.run(host='0.0.0.0', port = '80')

