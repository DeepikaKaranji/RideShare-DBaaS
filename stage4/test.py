where = "username = user1"
cn= ["password"]
tn = "user_details"
#msg = "{\"data\:"+data+",\"column\":"+cn+",\"table\":"+tn+"}"
x="{\"data\":\"Kritika\",\"cn\":\"NAme\",\"table\":\"user\"}"
test= "{\"where\": "+"\"" + where + "\"" + ", \"table\"" +":"+ "\"" + tn + "\"" + ",\"column\" : [ "
for i in range(0,len(cn)-1):
     test= test+ "\"" +cn[i] + "\"" + ","
test= test + "\"" + cn[len(cn)-1] + "\" ] }"
print(test)
 
