import datetime
import socketio
import eventlet
import time
import json

#threads
import threading
import os

#database
#import mysql.connector
#from datetime import datetime

#nostosdb = mysql.connector.connect(
 #   host = 'localhost',
#    user = 'root',
#    passwd = 'quandaledinglestudios3',
    #database ='nostosdb'
#)


#nostoscommand = "INSERT INTO requests (RID,userid,location,room_number,task,priority,people_amount,time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"

#print(nostosdb) 

#nostoscur = nostosdb.cursor()
#nostoscur.execute("SELECT * FROM users;")
#user_fetch = nostoscur.fetchall()
#nostoscur.execute("SELECT * FROM grooms;")
#groom_fetch = nostoscur.fetchall()
#for row in user_fetch:
 #print(row)
#for row in groom_fetch:
 #print(row)




########################################################
# pending requests list
requests_list = [
    
]
########################################################

########################################################
connected_clients = {}
connected_users = []
connected_grooms = []

#for break
active_grooms = [ ]

breaking_grooms = [ ]

break_timers = {}

#break in users screen
break_emiter = {}

#for overide
overrider = {}
########################################################


sio = socketio.Server(cors_allowed_origins='*')  #takes from all
app = socketio.WSGIApp(sio)



########################################################
#connect//establish connection and print the main sid that connected to the server
@sio.event
def connect(sid, environ):
    print(f"Client connected: {sid}")
    
########################################################
#dihsconnect disconnect the user from the server deleting its username from the the connected list hes is un and his sid-name tuple from the client list
@sio.event
def disconnect(sid):
    print(f"Client disconnected: {sid}")
    username = connected_clients.pop(sid, None)
    if username:
        if username in connected_users:
            connected_users.remove(username)
        elif username in connected_grooms:
            connected_grooms.remove(username)
        print(f"Removed {username} from connected lists")

########################################################
#kaspea - testing message from the client for debugging purposes
@sio.event
def Test(sid, data):
    print(f"Received from {sid}: {data}")
    sio.emit('Response', f"Server received: {data}")  

########################################################################################################################################################################
# Login event//handle connection and reconnection as the user/groom to the app 
@sio.event
def login(sid, data):
    user_id = data.get("id") #get the user id

    old_sid = None #at start the user has no sid unless we find out he is in the the client list already

    for sid_, uid in connected_clients.items(): #try to find the user id in the connected client list and if you do take the sid to old sid variable
        if uid == user_id:
            old_sid = sid_ #we will use this in the client list
            break

    if old_sid: # if old sid is changed mark reconnection and remove the sid for the current user in the connected client list to 
        print(f"User {user_id} reconnected! Old SID: {old_sid}, New SID: {sid}")
        connected_clients.pop(old_sid)

    
    if any(use['id'] == user_id for use in connected_users): #search again for the user id only this time in the user list
        sio.emit('amiin', {"iamin": True}, to=sid) #if found emit something to the app telling that the user is aleady in
        print("User Reconnected") #mark reconection again for debugging purposes
        sio.emit('login_response', {"success": True, "id": user_id, "job": "user"}, to=sid) #emit standart login message that allows the user to move forward to the app
        connected_clients[sid] = user_id  #change the sid for the current user since it changed and we already deleted the opd one earlier


        ############################ EXACT SAME THING FOR GROOMS AND CONNECTED_GROOM LIST ############################
    elif any(groo['id'] == user_id for groo in connected_grooms):
        sio.emit('amiin', {"iaming": True}, to=sid)
        print("Groom Reconnected")
        sio.emit('login_response', {"success": True, "id": user_id, "job": "groom"}, to=sid)
        connected_clients[sid] = user_id
    else:

       ############################ STANDART LOGIN FUNCTIONALITY // IF THE USER/GROOM IS NOT IN THE CONNECTED LISTS ############################
     if any(user['id'] == user_id and user['status'] == 'active'for user in users): #search for the user id in allowed users list // check if the username is allowed
        print(f"✅ Login success for {user_id}") #if it is mark connecton
        connected_users.append({"id": user_id,"page":False,"timebool":False}) #add the user id along with page and timebool parameters to the connected users list
        connected_clients[sid] = user_id # add the user id and sid pair to the connected clients list
        sio.emit('login_response', {"success": True, "id": user_id, "job": "user"}, to=sid) # emit standart login message that allows the user to move forward to the app


        ############################ EXACT SAME THING FOR GROOMS AND CONNECTED_GROOM LIST ############################
     elif any(groom['id'] == user_id and groom['status'] == 'active' for groom in grooms):
        print(f"✅ Login success for {user_id}")
        connected_grooms.append({"id": user_id})
        active_grooms.append(user_id)
        connected_clients[sid] = user_id
        sio.emit('login_response', {"success": True, "id": user_id, "job": "groom"}, to=sid)
     else:
        print(f"❌ Login failed for {user_id}")
        sio.emit('login_response', {"success": False}, to=sid)
    print(connected_users)
    print("Connected Clients", connected_clients)
########################################################################################################################################################################


####################################################################################
# locator / new request event 
@sio.event
def locator(sid, data):
    ###get all the app sends//info about the request###
    location = data.get("location")
    room_number = data.get("Room Number")
    task = data.get("Task")
    dropdown = data.get("DropDown")
    counter = data.get("Counter")
    RID = data.get("RID")



    user_id = connected_clients[sid] # get the username cause we will need it from the connected_clients list since we have the sid
    print(f"New request from {user_id} at {location}") #mark new request
    sio.emit("Status",{"accepted":True}) #emit stats message that informs that the request is accepted by the server so the user can move to the loading screen
   
    # add to the requests list// add the current information to the requst list for the current user
    requests_list.append({
        "user": user_id,
        "location": location,
        "room_number": room_number,
        "task":task,
        "dropdown":dropdown,
        "counter":counter,
        "time":0,
        "accepted": False,   
        "RID": RID,
        "timebool": True,
    })
    now = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    values = (RID,user_id,location,room_number,task,dropdown,counter,now)
    #nostoscur.execute(nostoscommand,values)
    #nostosdb.commit()
    
   
    
   
    for user in connected_users:
        if user["id"] == user_id: 
            #change the page and timebool variables to true for the current user
            user["page"] = True #page is set to true telling the server that the user is actually waiting for pickup so in case of a reconnection the user just goes to the same wating line waiting to get picked up
            user["timebool"] = True #timebool is responsible for starting a timer for the user that counts how many minutes he is waiting
            break

       
    eventlet.spawn(time_counter, RID) #spawn a counter for this request// create an cpu-load friendly *thread* that is responsible for running the counter for the current user
    eventlet.spawn(request_sender,sid,user_id)


    print(requests_list) #debug message 
    print(connected_users) #debug message
####################################################################################
    
   
####################################################################################
@sio.event
def delivery(sid, data):
    groom_id = data.get("groom")
    action = data.get("action")
    location = data.get("location") #get the emited location
    user_id = data.get("userId") #get the emited user_id
    RID = data.get("RID")
    if(action == 0):

     
   
     for req in requests_list:
      if req["RID"] == RID:
         req["accepted"] = True
         break
     #more could be here but they are not cause they are not needed and we save as much space as we can

     
     overrider[RID] = groom_id
     accepted = data.get("accepted") #get the accepted value it will be false and it probably isnt needed but for debug purposes its here
     #index = data.get("index") # index is an expiramnetal way of finding the groom in the list so the server doesnt have to look trough the list again
     #requests_list[index]["accepted"] = True #trhrough the expiramental index we search less and we change the accepted variable of the requests_list without having to search the connected_users again
     print(f"The groom: {groom_id} accepted pickup job from {location} with RID {RID}") #mark what happened
     #sio.emit("delivery_request",{"acception":True})
    else:
       
        overrided_groom = overrider[RID]
            
        
        target_sid = None
        for s, uid in connected_clients.items():
         if uid == overrided_groom:
            target_sid = s
            break
        print(f"Groom {groom_id} overrided call of groom {overrided_groom} (SID: {target_sid}) the requests was sent by {user_id}")
        sio.emit("override",{"override":True},to=target_sid)
        sio.emit("call_thief","move",to=sid)
        overrider[RID] = groom_id


####################################################################################

####################################################################################
@sio.event
def Arrived(sid, data):
    

    user_id = data.get("useridPick") #the user_id of the grooms choise
    RID = data.get("RID")
    arrive = data.get("Accepted") #tell the server that this request was accpeted // probably not needed
    print("user id = " + user_id) #debug
    print(connected_clients) #debug
    # find the target sid for the userid 
    target_sid = None
    for s, uid in connected_clients.items():
        if uid == user_id:
            target_sid = s
            break
   

    if target_sid is not None:#if its found
        for user in connected_users: #find the user id in the users and for that user id turn off page and timebool
            if user["id"] == user_id:
                user["page"] = False
                user["timebool"] = False
        sio.emit("finished", {"state": True,"RID": RID}, to=target_sid) #emit this message to the client ( to the user id we found ) so the waiting state is off // probably not needed
        for i, req in enumerate(requests_list): #find the user id in the requests_list and delete everything associated with that user id aka delete the request
                  requests_list[:] = [req for req in requests_list if req["RID"] != RID]
                  print(requests_list) # mark the findings for debug purposes
        print(f"➡️ Emitting 'finished' to SID: {target_sid} with data: {{'state': True}}") #mark the finish
        print("Current connected_clients:", connected_clients) #mark the connected clinets list again for debug purposes
    else:
        print(f"Warning: user_id {user_id} not found in connected_clients") # if the user id is not found in the current users the user is not in but delete anything associated with that user id anyway
        requests_list[:] = [req for req in requests_list if req["RID"] != RID]
        print(requests_list)
    ####################################################################################

    ####################################################################################
@sio.event
def Break(sid, data):
   reason = data.get("reason")
   user_id = data.get("userid")
   if(reason != "stop"):
     print("user",user_id," takes a break with reason: ",reason)
     active_grooms.remove(user_id) 
     breaking_grooms.append(user_id)
     sio.emit("break_confirmation",{"confirmation":True},to=sid)
     break_timers[user_id] = True
     thread = eventlet.spawn(break_clock,user_id)
        #start a timer with a function
   else:
       break_timers[user_id] = False
       active_grooms.append(user_id)
       breaking_grooms.remove(user_id)
       

 

    ####################################################################################

    ####################################################################################
@sio.event
def seeBreaks(sid,data):
    see = data.get("seeBreaks")
    user_id = connected_clients[sid] 
    if(see == True):
     print(f"User: {user_id} started seeing the Grooms' breaks")
     break_emiter[user_id] = True
     eventlet.spawn(Breaking_Grooms,user_id)
    else:
     break_emiter[user_id] = False
     print(f"User: {user_id} stopped seeing the Grooms' breaks")
    

    ####################################################################################
    




    #THESE FUNCTIONS HELP WITH THE REST OF THE PROGRAM AND ARE NOT EVENTS
    #broadcast_requests sends the requests to the clients every second
    #time counter is responsible for running counters
    #get_timebool takes the timebool variable from the connected_users list so it always knows if it should stop the timer or not
    #update_user_time is an expiramental function that finds the user in the requests_list and changes the time that he is in
####################################################################################
def broadcast_requests():
    while True:
        for sid, user_id in connected_clients.items():
          for user in connected_users:
            if user["id"] == user_id:
              sio.emit("Page", {"status": user["page"]}, to=sid)
              break



              
        #print(Page)
        sio.emit("Board", requests_list)
        eventlet.sleep(1)  # non-blocking sleep
        #print("sent") 
####################################################################################

####################################################################################
def time_counter(RID):
    while True:
        # find the request by RID
        req = next((r for r in requests_list if r["RID"] == RID), None)
        if not req or not req["timebool"]:
            break
        eventlet.sleep(1)
        req["time"] += 1

def request_sender(sid,user_id):

    request_box = [ ]
    for req in requests_list:
     if req["user"] == user_id:
        request_box.append(req)

    sio.emit("myrequest",{"myrequest":request_box},to=sid)


BASE_PATH = "C:/Users/user/Desktop/TESTING"




#Load from database
#users = [
  #  {'id': user_id, 'status': 'active' if status == 1 else 'inactive'}
 #   for user_id, status in user_fetch
#]
#print("✅ Loaded users:", users)

#grooms = [
  #  {'id': user_id, 'status': 'active' if status == 1 else 'inactive'}
  #  for user_id, status in groom_fetch
#]
#print("✅ Loaded grooms:", grooms)
users = [
    {'id': f'user00{i}', 'status': 'active'} for i in range(1, 11)
]
print("✅ Loaded users:", users)

grooms = [
    {'id': f'groom00{i}', 'status': 'active'} for i in range(1, 11)
]
print("✅ Loaded grooms:", grooms)




def timer():
   timer = 0
   minutes = 0
   hours = 0
   days = 0
   weeks = 0
   while(True):
       eventlet.sleep(1)
       timer+=1
       seconds = timer%60
       if(seconds%60 == 0): #> for tests
           minutes+=1

       if(minutes >= 60): #> for tests
        minutes = 0
        hours+=1

       if(hours >= 24): #> for tests
        hours = 0
        days+=1

       if(days >= 7): #> for tests
        days = 0
        weeks+=1
       

      
      
    
       #print(weeks,"/",days,"/",hours,"/",minutes,"/",seconds)



def break_clock(user_id):
    target_sid = None
    for s, uid in connected_clients.items():
        if uid == user_id:
            target_sid = s
            break

    counter = 0
    while(break_timers[user_id] == True):
        eventlet.sleep(1)
        counter+=1
        sio.emit("breaking_time",{"time":counter},to=target_sid)
    print("timer for groom:", user_id, 'was terminated he stoped jerking off')

def sort_requests(requests):
    time  = requests["time"]

def Breaking_Grooms(user_id):
    target_sid = None
    for s, uid in connected_clients.items():
        if uid == user_id:
            target_sid = s
            break

    while( break_emiter[user_id] == True):
     eventlet.sleep(1)
     sio.emit("breaking_grooms",{"list":breaking_grooms},to=target_sid) # maybe i need to find it with the username



####################################################################################
#run
if __name__ == '__main__':
    eventlet.spawn(broadcast_requests)
    eventlet.spawn(timer)
    print("Socket.IO server running on http://192.168.1.2:5000")
    eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 5000)), app)
####################################################################################