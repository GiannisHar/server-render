from datetime import datetime

import socketio
import asyncio
from aiohttp import web

from eventlet.semaphore import Semaphore
import time
import json

#threads
import threading
import os

valid_rooms = set()
########################################################
# pending requests list
requests_list = [
    
]
request_timestamps = {}

#requests_list_semaphore = Semaphore()
requests_list_semaphore = asyncio.Lock()

groom_accepted_requests = {}
user_active_requests = {}

########################################################

########################################################
connected_clients = {}
connected_clients_via_userid = {}

connected_clients_jobs = {}



connected_users = []
connected_grooms = []
########################################################

########################################################
#for disconnect and battery assisted logic

user_battery = {}
wakelock_mode = set()

paused_app = set()
detached_app = set()
########################################################

########################################################
###modes###
mode = {}
########################################################
#for break
active_grooms = [ ]

breaking_grooms = [ ]

break_timers = {}

#break in users screen
break_emiter = {}

#for overide
overrider = {}
########################################################

########################################################
#for no dupicates of the accepted list 

accepted_rids = set() #set doesnt permit duplicates
overrided_rid = set()

########################################################

#for attention
attentions_list = [
    
]



sio = socketio.AsyncServer(
    cors_allowed_origins='*',  
    async_mode='aiohttp',       
    transports=['websocket']    
)
app = web.Application()
sio.attach(app)


@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    print(connected_clients) 
    
@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

@sio.event  
async def app_paused(sid,data):
    user_id = data.get("user_id")
    job = data.get("job")


    if job == "groom":
     battery_info = user_battery.get(user_id)
     if battery_info is not None:
      battery = battery_info["battery"]
      charging = battery_info["charging"]
     else:
      battery = 771 #unreal number that fits
      charging = None

     if battery <= 5 and charging != "BatteryState.charging":
      rid_list = [req["RID"] for req in groom_accepted_requests.get(user_id,[])]
      for req in requests_list:
         if req["RID"] in rid_list:
             req["accepted"] = False
      accepted_rids.difference_update(rid_list)
      groom_accepted_requests[user_id] = []
      print(f"[/!\\] Groom: {user_id} got away")
     else:
         print(f"Groom: {user_id} disconnected but most likely will return soon ")
    else:
        print(f"User: {user_id} either disconnected or just got away")



    



@sio.event 
async def app_closed(sid,data):
    user_id = data.get("user_id")
    detached_app.add(user_id)
    job = data.get("job")
    print("[DETACHING]")


@sio.event 
async def battery(sid,data):
   user_id = data.get("user_id")
   battery = data.get("battery")
   charging = data.get("charging")
   wakeclock = data.get("wakeclock")
   user_battery[user_id] = {"battery":battery,"charging":charging}
   if battery is None:
    battery = 771;
   if charging is None:
    charging = None

   if battery <= 5 and charging != "BatteryState.charging" and user_id not in wakelock_mode:
    await sio.emit("Low_Battery",{"act":True},to=sid)
    wakelock_mode.add(user_id)
    print(f"Groom {user_id} Has Low Battery: {battery} Switching to Wakelock Mode")
   elif (battery > 5 or charging == "BatteryState.charging") and user_id in wakelock_mode:
    await sio.emit("Low_Battery",{"act":False},to=sid)
    wakelock_mode.discard(user_id)
    print(f"Groom {user_id} Has High Battery: {battery} or is Charging his Phone Switching to Normal Mode")



@sio.event
async def Test(sid, data):
    print(f"Received from {sid}: {data}")
    await sio.emit('Response', f"Server received: {data}")  

@sio.event
async def login(sid, data):
    user_id = data.get("id") #get the user id
    reconnect_singal = data.get("reconnect")

    old_sid = None #at start the user has no sid unless we find out he is in the the client list already

    for sid_, uid in connected_clients.items(): #try to find the user id in the connected client list and if you do take the sid to old sid variable
        if uid == user_id:
            old_sid = sid_ #we will use this in the client list
            break

    if old_sid: # if old sid is changed mark reconnection and remove the sid for the current user in the connected client list to 
        print(f"User {user_id} reconnected! Old SID: {old_sid}, New SID: {sid}")
        connected_clients.pop(old_sid)
        connected_clients_jobs.pop(old_sid)







    if any(use['id'] == user_id for use in connected_users): #search again for the user id only this time in the user list
        await sio.emit('amiin', {"iamin": True}, to=sid) #if found emit something to the app telling that the user is aleady in
        print("User Reconnected") #mark reconection again for debugging purposes
        #sio.emit('login_response', {"success": True, "id": user_id, "job": "user","recon":True,"mode":mode[user_id]}, to=sid) #emit standart login message that allows the user to move forward to the app
        connected_clients[sid] = user_id  #change the sid for the current user since it changed and we already deleted the opd one earlier
        connected_clients_via_userid[user_id] = sid
        connected_clients_jobs[sid] = "user"
        #mode[user_id] = data.get("mode")
        await mode_handler(user_id,sid,reconnect_singal,"user")





        ############################ EXACT SAME THING FOR GROOMS AND CONNECTED_GROOM LIST ############################
    elif any(groo['id'] == user_id for groo in connected_grooms):
        await sio.emit('amiin', {"iaming": True}, to=sid)
        print("Groom Reconnected")
        #sio.emit('login_response', {"success": True, "id": user_id, "job": "groom","recon":True,"mode":mode[user_id]}, to=sid)
        connected_clients[sid] = user_id
        connected_clients_via_userid[user_id] = sid
        connected_clients_jobs[sid] = "groom"
        #mode[user_id] = data.get("mode")
        await mode_handler(user_id,sid,reconnect_singal,"groom")
    










    else:
        #or (user['id'] == 'benchmarker' and user['status'] == 'active' for user in users)
       ############################ STANDART LOGIN FUNCTIONALITY // IF THE USER/GROOM IS NOT IN THE CONNECTED LISTS ############################
     if any(user['id'] == user_id and user['status'] == 'active'for user in users) or (user_id =='benchmarker'): #search for the user id in allowed users list // check if the username is allowed
        print(f"✅ Login success for {user_id}") #if it is mark connecton
        connected_users.append({"id": user_id,"page":False,"timebool":False}) #add the user id along with page and timebool parameters to the connected users list
        connected_clients[sid] = user_id # add the user id and sid pair to the connected clients list
        connected_clients_via_userid[user_id] = sid
        connected_clients_jobs[sid] = "user"
        mode[user_id] = "Login"
        await sio.emit('login_response', {"success": True, "id": user_id, "job": "user","mode":mode[user_id],"recon":False}, to=sid) # emit standart login message that allows the user to move forward to the app


        ############################ EXACT SAME THING FOR GROOMS AND CONNECTED_GROOM LIST ############################
     elif any(groom['id'] == user_id and groom['status'] == 'active' for groom in grooms) or (user_id == 'pmurans') or (user_id == 'kandreadis'):
        print(f"✅ Login success for {user_id}")
        connected_grooms.append({"id": user_id})
        active_grooms.append(user_id)
        connected_clients[sid] = user_id
        connected_clients_via_userid[user_id] = sid
        connected_clients_jobs[sid] = "groom"
        mode[user_id] = "Login"
        await sio.emit('login_response', {"success": True, "id": user_id, "job": "groom","mode":mode[user_id],"recon":False}, to=sid)
        #groom_accepted_requests[user_id] = []
     else:
        print(f"❌ Login failed for {user_id}")
        await sio.emit('login_response', {"success": False}, to=sid)
    print(connected_users)
    print("Connected Clients", connected_clients)
    print("Connected Clients Jobs", connected_clients_jobs)
########################################################################################################################################################################

@sio.event
async def locator(sid, data):

    global requests_list

    ###get all the app sends//info about the request###
    location = data.get("location")
    room_number = data.get("Room Number")
    task = data.get("Task")
    dropdown = data.get("DropDown")
    counter = data.get("Counter")
    RID = data.get("RID")

    
    timestamp = datetime.now().strftime("%H:%M")
    request_timestamps[RID] = timestamp
    print(f"[TIME] {timestamp}")


    user_id = connected_clients[sid] # get the username cause we will need it from the connected_clients list since we have the sid
    print(f"New request from {user_id} at {location}") #mark new request
    await sio.emit("Status",{"accepted":True},to=sid) #emit stats message that informs that the request is accepted by the server so the user can move to the loading screen
    
    # add to the requests list// add the current information to the requst list for the current user
    async with requests_list_semaphore:
        # prevent duplicate requests
      if any(r["RID"] == RID for r in requests_list):
          print("[!] Duplicate was found {?}: Rare same rid ocasion proves time based handling needs to be implemented")
          return


      request = {
       "user": user_id,
       "location": location,
       "room_number":room_number,
       "task": task,
       "dropdown":dropdown,
       "counter": counter,
       "time":request_timestamps[RID],
       "accepted":False, #unessesary
       "RID": RID,
       "timebool":True
                 }   

      created_ts = int(datetime.now().timestamp())
      requests_list.append({
        "user": user_id,
        "location": location,
        "room_number": room_number,
        "task":task,
        "dropdown":dropdown,
        "counter":counter,
        "time":created_ts,
        "elapsed": 0,
        "accepted": False,   
        "RID": RID,
        "timebool": True,
        
      })
      requests_list = await SortRequestsList(requests_list)
    #now = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    #values = (RID,user_id,location,room_number,task,dropdown,counter,now)
    #nostoscur.execute(nostoscommand,values)
    #nostosdb.commit()
    
    if user_id not in user_active_requests:
     user_active_requests[user_id] = []
   
    user_active_requests[user_id].append(request)
   
    ### this may be unneeded
    for user in connected_users:
        if user["id"] == user_id: 
            #change the page and timebool variables to true for the current user
            user["page"] = True #page is set to true telling the server that the user is actually waiting for pickup so in case of a reconnection the user just goes to the same wating line waiting to get picked up
            user["timebool"] = True #timebool is responsible for starting a timer for the user that counts how many minutes he is waiting
            break
        
       
    asyncio.create_task(time_counter(RID)) #spawn a counter for this request// create an cpu-load friendly *thread* that is responsible for running the counter for the current user
    #eventlet.spawn(request_sender,sid,user_id)
    
    asyncio.create_task(broadcast_user_active_requests(user_id, sid))
    asyncio.create_task(broadcast_requests(sid))
    asyncio.create_task(broadcast_timestamps())
    print(requests_list) #debug message 
    print(connected_users) #debug message
####################################################################################
####################################################################################
@sio.event 
async def get_accepted_requests(sid,data):
    user_id = data.get("user_id")
    mode = data.get("mode")
    
    asyncio.create_task(broadcast_accepted_requests(user_id,sid))

####################################################################################

####################################################################################
@sio.event 
async def get_user_active_requests(sid,data):
    user_id = data.get("user_id")
    mode = data.get("mode")
    asyncio.create_task(broadcast_user_active_requests(user_id, sid))

@sio.event 
async def delete_request(sid,data):
    RID = data.get("RID")
    user_id = data.get("user_id")

    print(f"[DELETE] User {user_id} requested delete for RID {RID}")

    requests_list[:] = [r for r in requests_list if r["RID"] != RID]

    request_timestamps.pop(RID, None)

    # remove from user active
    user_active_requests[user_id] = [
        r for r in user_active_requests.get(user_id, [])
        if r["RID"] != RID
    ]

    # remove from groom accepted
    for groom_id, reqs in groom_accepted_requests.items():
        groom_accepted_requests[groom_id] = [
            r for r in reqs if r["RID"] != RID
        ]

    accepted_rids.discard(RID)

    # broadcast updates
    asyncio.create_task(broadcast_requests(sid))
    asyncio.create_task(broadcast_accepted_requests(user_id,-1))
    asyncio.create_task(broadcast_user_active_requests(user_id, sid))

    print(f"[DELETE] RID {RID} fully removed")



####################################################################################
   

####################################################################################
@sio.event
async def delivery(sid, data):
    groom_id = data.get("groom")
    action = data.get("action")

    RID = data.get("RID")
    user_id = data.get("userId") #get the emited user_id
    location = data.get("location") #get the emited location
    room_number = data.get("room_number")
    task = data.get("task")
    dropdown = data.get("dropdown")
    counter = data.get("counter")
    accepted_info = data.get("accepted") #unessesary
    index = data.get("index")
    time = data.get("time") #time screenshot

    request = {
    
    "userId": user_id,
    "location": location,
    "room_number":room_number,
    "task": task,
    "dropdown":dropdown,
    "counter": counter,
    "time":time,
    "accepted":accepted_info, #unessesary
    "index":index,
    "RID": RID
}   

    if groom_id not in groom_accepted_requests:
     groom_accepted_requests[groom_id] = []

    if(action == 0):


       req = next((r for r in requests_list if r["RID"] == RID), None)

       if RID in accepted_rids:
        # Already taken
        await sio.emit("call_taken", {"taken_rid": RID}, to=sid)
        return 
        

       accepted_rids.add(RID)
       groom_accepted_requests[groom_id].append(request)
       req["accepted"] = True
       overrider[RID] = groom_id
       await sio.emit("permition_granded", {"taken_rid": RID}, to=sid)
       print("granded permition")

       accepted = data.get("accepted") #get the accepted value it will be false and it probably isnt needed but for debug purposes its here
       print(f"The groom: {groom_id} accepted pickup job from {location} with RID {RID}") #mark what happened
       asyncio.create_task(broadcast_requests(connected_clients_via_userid[groom_id]))
       

       print(accepted_rids)

    else:
       
        overrided_groom = overrider[RID]
        #groom_accepted_requests  

        target_sid = connected_clients_via_userid[overrided_groom]

        requests_from = groom_accepted_requests.get(overrided_groom, [])

        request_to_move = None
        for deq in requests_from:
          if deq["RID"] == RID:
            request_to_move = deq
            break

        if request_to_move:
          requests_from.remove(request_to_move)                  
          groom_accepted_requests[groom_id].append(request_to_move)  
          groom_accepted_requests[overrided_groom] = requests_from

        
        print(f"Groom {groom_id} overrided call of groom {overrided_groom} (SID: {target_sid}) the requests was sent by {user_id}")



        await sio.emit("override",{"override":True,"RID":RID},to=target_sid)

        #sio.emit("call_thief",{"RID":RID},to=sid)


        overrider[RID] = groom_id
        
        asyncio.create_task(broadcast_accepted_requests(overrided_groom,target_sid))
        asyncio.create_task(broadcast_requests(sid))
        asyncio.create_task(broadcast_accepted_requests(groom_id,sid))
        asyncio.create_task(broadcast_timestamps()) 
        
    asyncio.create_task(broadcast_requests(sid))
    asyncio.create_task(broadcast_accepted_requests(groom_id,sid))
    asyncio.create_task(broadcast_timestamps())   

     
        


####################################################################################

####################################################################################
@sio.event
async def groom_declined(sid,data):
    groom_id = data.get("groom")
    RID = data.get("RID")
    print("rid",RID)

    for req in requests_list:
      if req["RID"] == RID:
         req["accepted"] = False
         accepted_rids.remove(RID)
         break
     
    asyncio.create_task(broadcast_requests(connected_clients_via_userid[groom_id]))
    requests = groom_accepted_requests.get(groom_id, [])
    asyncio.create_task(broadcast_accepted_requests(groom_id,sid))
    groom_accepted_requests[groom_id] = [deq for deq in requests if deq["RID"] != RID]

@sio.event
async def Arrived(sid, data):
    
    groom_id = data.get("groom")
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
        await sio.emit("finished", {"state": True,"RID": RID}, to=target_sid) #emit this message to the client ( to the user id we found ) so the waiting state is off // probably not needed
        
        #for i, req in enumerate(requests_list): #find the user id in the requests_list and delete everything associated with that user id aka delete the request
        requests_list[:] = [req for req in requests_list if req["RID"] != RID]
        request_timestamps.pop(RID, None)



        requests = groom_accepted_requests.get(groom_id, [])
        #user_requests = user_active_requests.get(user_d,[])
        groom_accepted_requests[groom_id] = [deq for deq in requests if deq["RID"] != RID]
        
        user_active_requests[user_id] = [
        r for r in user_active_requests.get(user_id, [])
        if r["RID"] != RID
    ]

        print(requests_list)
        print(requests_list) # mark the findings for debug purposes
        print(request_timestamps)
        print(f"➡️ Emitting 'finished' to SID: {target_sid} with data: {{'state': True}}") #mark the finish
        print("Current connected_clients:", connected_clients) #mark the connected clinets list again for debug purposes

    else:
        print(f"Warning: user_id {user_id} not found in connected_clients") # if the user id is not found in the current users the user is not in but delete anything associated with that user id anyway
        
        requests_list[:] = [req for req in requests_list if req["RID"] != RID]
        request_timestamps.pop(RID, None)
        requests = groom_accepted_requests.get(groom_id, [])

        groom_accepted_requests[groom_id] = [deq for deq in requests if deq["RID"] != RID]
        
        user_active_requests[user_id] = [
        r for r in user_active_requests.get(user_id, [])
        if r["RID"] != RID
    ]
    
        print(requests_list)
        print(request_timestamps)
        print(user_active_requests[user_id])
    
    asyncio.create_task(broadcast_requests(sid))
    asyncio.create_task(broadcast_accepted_requests(groom_id,sid))
    asyncio.create_task(broadcast_user_active_requests(user_id,target_sid))
    asyncio.create_task(broadcast_timestamps())

    ####################################################################################

    ####################################################################################
@sio.event
async def Break(sid, data):
   reason = data.get("reason")
   user_id = data.get("userid")

  


   if(reason != "stop"):
     print("user",user_id," takes a break with reason: ",reason)
     active_grooms.remove(user_id) 
     breaking_grooms.append(user_id)
     await sio.emit("break_confirmation",{"confirmation":True},to=connected_clients_via_userid[user_id])
     break_timers[user_id] = True
     thread = asyncio.create_task(break_clock(user_id))
        #start a timer with a function
   else:
       break_timers[user_id] = False
       active_grooms.append(user_id)
       breaking_grooms.remove(user_id)
       

 

    ####################################################################################

    ####################################################################################
@sio.event
async def seeBreaks(sid,data):
    see = data.get("seeBreaks")
    user_id = connected_clients[sid] 
    if(see == True):
     print(f"User: {user_id} started seeing the Grooms' breaks")
     break_emiter[user_id] = True
     asyncio.create_task(Breaking_Grooms(user_id))
    else:
     break_emiter[user_id] = False
     print(f"User: {user_id} stopped seeing the Grooms' breaks")
    

    ####################################################################################

@sio.event
async def update(sid,data):
 print("[!][!][!]Update Event Accessed")
 user_id = data.get("user_id")
 asyncio.create_task(broadcast_requests(1))#connected_clients_via_userid[user_id])
 asyncio.create_task(broadcast_timestamps())
            
 #####$$$$$$ THIS SENDS THE UPDATE MESSAGES TO EVERYONE AND IT NEEDS TO BE MADE SO IT SENDS THE UPDATES ONLY TO USERS $$$$$$#####
@sio.event 
async def AttentionAddition(sid,data):
    addition = data.get("addition")
    attentions_list.append(addition)
    print(attentions_list)
    await sio.emit("AttentionList", {
        "list": attentions_list
    })

@sio.event
async def AttentionRemoval(sid,data):
    index = data.get("index")
    attentions_list.pop(index)
    print(attentions_list)
    await sio.emit("AttentionList", {
        "list": attentions_list
    })


@sio.event
async def send_attention_list(sid):
    await sio.emit("AttentionList", {
        "list": attentions_list
    }, to=sid)



@sio.event 
async def mode_updater(sid,data):
    user_id = data.get("user_id")
    mode[user_id] = data.get("mode")
    print(f"[MODE!] mode for user {user_id} was changed to {mode[user_id]}")



@sio.event 
async def personal_requests(sid,data):
    user_id = data.get("user_id")


async def mode_handler(user_id,sid,recon,job):
    mode_handled = mode[user_id] 
    if(recon == True):
      match mode_handled:
        case "Login":
            await sio.emit("Mode Handlder", {"mode":mode_handled})
        case "Break":
            await sio.emit("Mode Handlder", {"mode":mode_handled})
        case "Accepted_List":
            await sio.emit("Mode Handlder", {"mode":mode_handled})
            asyncio.create_task(broadcast_requests(sid))
            asyncio.create_task(broadcast_timestamps())
        case "Requests_List":
            await sio.emit("Mode Handlder", {"mode":mode_handled})
            asyncio.create_task(broadcast_requests(sid))
            asyncio.create_task(broadcast_timestamps())
            

    else:
            isb = False
            if user_id in breaking_grooms:
                isb = True 

            print(f"[!!!]{isb}")
            await sio.emit('login_response', {"success": True, "id": user_id, "job": job,"recon":True,"mode":mode_handled,"is_breaking":isb}, to=sid) 
            #broadcast_timestamps()

async def broadcast_requests(sid):
   print("get ready")
   print(sid)
   #print(connected_users)
   #print(connected_grooms)
   #print(connected_clients)
   for i in range(5):
     #sio.emit("Board", requests_list,to=sid)
     await sio.emit("Board", requests_list)
     await asyncio.sleep(1)


async def broadcast_timestamps():
    for i in range(5):
        #for rid, ts in request_timestamps.items():
        #for rid, ts in list(request_timestamps.items()):
        snapshot = request_timestamps.copy()
        for rid, ts in snapshot.items():
            await sio.emit("timestamp", {"RID": rid, "timestamp": ts})
        await asyncio.sleep(1)  # emit every second
   
    #THESE FUNCTIONS HELP WITH THE REST OF THE PROGRAM AND ARE NOT EVENTS
    #broadcast_requests sends the requests to the clients every second
    #time counter is responsible for running counters
    #get_timebool takes the timebool variable from the connected_users list so it always knows if it should stop the timer or not
    #update_user_time is an expiramental function that finds the user in the requests_list and changes the time that he is in


async def broadcast_accepted_requests(groom_id,sid):
   print("get ready")
   print(sid)
   #print(connected_users)
   #print(connected_grooms)
   #print(connected_clients)
   if groom_id not in groom_accepted_requests:
    groom_accepted_requests[groom_id] = []
   if sid != -1:
    for i in range(5):
      #sio.emit("Board", requests_list,to=sid)
      await sio.emit("accepted_requests",groom_accepted_requests[groom_id],to=sid)
      await asyncio.sleep(1)
   else:
      for target_sid, job in connected_clients_jobs.items():
         if job != "groom":
            continue

         groom_id = connected_clients[target_sid]
         if groom_id not in groom_accepted_requests:
            groom_accepted_requests[groom_id] = []
         await sio.emit("accepted_requests", groom_accepted_requests[groom_id],to=target_sid)






    


async def broadcast_user_active_requests(user_id,sid):
   print("get ready")
   print(sid)
   #print(connected_users)
   #print(connected_grooms)
   #print(connected_clients)
   if user_id not in user_active_requests:
    user_active_requests[user_id] = []
   for i in range(5):
     #sio.emit("Board", requests_list,to=sid)
     await sio.emit("user_active_requests",user_active_requests[user_id],to=sid)
     await asyncio.sleep(1)

####################################################################################
async def time_counter(RID):
    while True:
        # find the request by RID
        req = next((r for r in requests_list if r["RID"] == RID), None)
        if not req or not req["timebool"]:
            break
        await asyncio.sleep(1)
        req["elapsed"] += 1







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

grooms.append({'id':'pmurans','status':'active'})
grooms.append({'id':'kandreadis','status':'active'})
users.append({'id':'benchmarker','status':'active'})

async def timer():
   timer = 0
   minutes = 0
   hours = 0
   days = 0
   weeks = 0
   while(True):
       await asyncio.sleep(1)
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



async def break_clock(user_id):
    counter = 0
    while(break_timers[user_id] == True):
        await asyncio.sleep(1)
        counter+=1
        await sio.emit("breaking_time",{"time":counter},to=connected_clients_via_userid[user_id])
    print("timer for groom:", user_id, 'was terminated he stoped jerking off')

async def sort_requests(requests):
    time  = requests["time"]

async def Breaking_Grooms(user_id):
    while( break_emiter[user_id] == True):
     await asyncio.sleep(1)
     await sio.emit("breaking_grooms",{"list":breaking_grooms},to=connected_clients_via_userid[user_id]) # maybe i need to find it with the username


async def SortRequestsList(req_list):

    def attention_value(level):
        priority = {
            "VIP / Executives": 5,
            "Mobility Issues": 4,
            "Attention": 2,
            "C-Report": 3,
            "Repeaters": 1,
        }
        return priority.get(level, 0)

    def priority_key(req):
     accepted = req.get("accepted", False)
     time_bucket = req.get("elapsed", 0) // 120
     att = attention_value(req.get("dropdown", ""))

     if accepted:
        # Accepted requests go LAST no matter what
         return (1, 0, 0)

    # Non-accepted requests only compete with each other
     return (0, -time_bucket, -att)

    req_list.sort(key=priority_key)
    return req_list















if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=5000)