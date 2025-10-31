import socketio
import eventlet
import time

############################
###### users and grooms#####
users = [
    {"id": "user001"},
    {"id": "admin"}
]

grooms = [
    {"id": "groom001"}
]
############################


############################
# pending requests list
requests_list = [
    {"user": "usertemp",
    "location": "Lobby",
   "room_number": "0",
  "task":"temp",
 "dropdown":"temp",
"counter":0,
"time":0,
"accepted": False,},
]
############################

############################
connected_clients = {}
connected_users = [{"id":"","page":False,"timebool":False}]
connected_grooms = [{"id":""}]
############################



sio = socketio.Server(cors_allowed_origins='*')  #takes from all
app = socketio.WSGIApp(sio)



############################
#connect//establish connection and print the main sid that connected to the server
@sio.event
def connect(sid, environ):
    print(f"Client connected: {sid}")
    
############################
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

############################
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
     if any(user['id'] == user_id for user in users): #search for the user id in allowed users list // check if the username is allowed
        print(f"✅ Login success for {user_id}") #if it is mark connecton
        connected_users.append({"id": user_id,"page":False,"timebool":False}) #add the user id along with page and timebool parameters to the connected users list
        connected_clients[sid] = user_id # add the user id and sid pair to the connected clients list
        sio.emit('login_response', {"success": True, "id": user_id, "job": "user"}, to=sid) # emit standart login message that allows the user to move forward to the app


        ############################ EXACT SAME THING FOR GROOMS AND CONNECTED_GROOM LIST ############################
     elif any(groom['id'] == user_id for groom in grooms):
        print(f"✅ Login success for {user_id}")
        connected_grooms.append({"id": user_id})
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
        "accepted": False   
    })


   
    
   
    for user in connected_users:
        if user["id"] == user_id: 
            #change the page and timebool variables to true for the current user
            user["page"] = True #page is set to true telling the server that the user is actually waiting for pickup so in case of a reconnection the user just goes to the same wating line waiting to get picked up
            user["timebool"] = True #timebool is responsible for starting a timer for the user that counts how many minutes he is waiting
            break

        
        eventlet.spawn(time_counter, sid, user_id) #spawn a counter for this request// create an cpu-load friendly *thread* that is responsible for running the counter for the current user



    print(requests_list) #debug message 
    print(connected_users) #debug message
####################################################################################
    
   
####################################################################################
@sio.event
def delivery(sid, data):
    location = data.get("location") #get the emited location
    user_id = data.get("userId") #get the emited user_id
    #more could be here but they are not cause they are not needed and we save as much space as we can

    groom_id = connected_clients[sid] #get the groom_id from the connected clients
    accepted = data.get("accepted") #get the accepted value it will be false and it probably isnt needed but for debug purposes its here
    index = data.get("index") # index is an expiramnetal way of finding the groom in the list so the server doesnt have to look trough the list again
    requests_list[index]["accepted"] = True #trhrough the expiramental index we search less and we change the accepted variable of the requests_list without having to search the connected_users again
    print(f"The user: {groom_id} accepted pickup job from {location} at index {index}") #mark what happened
    #sio.emit("delivery_request",{"acception":True})
####################################################################################

####################################################################################
@sio.event
def Arrived(sid, data):
    

    user_id = data.get("useridPick") #the user_id of the grooms choise
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
        sio.emit("finished", {"state": True}, to=target_sid) #emit this message to the client ( to the user id we found ) so the waiting state is off // probably not needed
        for i, req in enumerate(requests_list): #find the user id in the requests_list and delete everything associated with that user id aka delete the request
               if req["user"] == user_id:
                  del requests_list[i]
                  break  # stop after deleting this
                  print(requests_list) # mark the findings for debug purposes
        print(f"➡️ Emitting 'finished' to SID: {target_sid} with data: {{'state': True}}") #mark the finish
        print("Current connected_clients:", connected_clients) #mark the connected clinets list again for debug purposes
    else:
        print(f"Warning: user_id {user_id} not found in connected_clients") # if the user id is not found in the current users the user is not in but delete anything associated with that user id anyway
        for i, req in enumerate(requests_list):
               if req["user"] == user_id:
                  del requests_list[i]
                  break  # stop after deleting this 
                  print(requests_list)
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
def time_counter(sid,user_id):

    print(f"Counter started for {user_id}")

    count = 0
    while(get_timebool(user_id) == True):

     eventlet.sleep(1)
     count +=1
     update_user_time(user_id, count)


     #get the timebool
def get_timebool(user_id):
    for user in connected_users:
        if user["id"] == user_id:
            return user["timebool"]
    return None  

     #change the time in the list all the time
def update_user_time(user_id, new_time):
    for req in requests_list:
        if req["user"] == user_id:
            req["time"] = new_time
            return True
    return False  
####################################################################################



####################################################################################
#run
if __name__ == '__main__':
    eventlet.spawn(broadcast_requests)
    print("Socket.IO server running on http://192.168.1.2:5000")
    eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 5000)), app)
####################################################################################