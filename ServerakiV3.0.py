from datetime import datetime
from sched import Event

import socketio
import asyncio
#import uvloop
#asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
from aiohttp import web

from eventlet.semaphore import Semaphore
import time
import json

#threads
import threading
import psutil
import os

import jwt
from datetime import datetime, timedelta, timezone
import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
ph = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=2)

#import mysql.connector
import psycopg2
from psycopg2 import sql

import asyncpg

from concurrent.futures import ThreadPoolExecutor

thread_pool = ThreadPoolExecutor(max_workers=4)

async def hash_password(password: str) -> str:
    loop = asyncio.get_event_loop()
    hashed = await loop.run_in_executor(
        thread_pool,
        lambda: ph.hash(password)
    )
    return hashed

async def check_password(password: str, hashed: str) -> bool:
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            thread_pool,
            lambda: ph.verify(hashed, password)
        )
        return True
    except VerifyMismatchError:
        return False

from collections import defaultdict

db_pool = None

#hashed = bcrypt.hashpw("user001".encode(), bcrypt.gensalt()).decode()
#print(hashed)




########################################################################################################################################################################



#nostosdb = mysql.connector.connect(
    #host = 'localhost',
    #user = 'root',
    #passwd = 'quandaledinglestudios3',
    #database ='nostosdb'
#)


nostoscommand = "INSERT INTO requests (RID,userid,location,room_number,task,priority,people_amount,time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
#nostoscur = nostosdb.cursor()
#print(nostosdb) 





rate_limits = defaultdict(list)

def is_rate_limited(user_id, limit=5, window=2):
    """Allows 'limit' requests per 'window' seconds."""
    now = time.time()
    # Keep only timestamps within the time window
    rate_limits[user_id] = [t for t in rate_limits[user_id] if now - t < window]
    
    if len(rate_limits[user_id]) >= limit:
        return True # User is sending too fast
        
    rate_limits[user_id].append(now)
    return False

########################################################################################################################################################################

#nostosdb = psycopg2.connect(
   # host="dpg-d676j98boq4c73fo1vig-a.frankfurt-postgres.render.com",
   # user="nostosdb",
   # password="czLedw1jFvolK7xiGeMytLmwpy5mZrBO",
  #  dbname="nostosdb",
   # port=5432,
   # sslmode="prefer"
#)
#host = os.getenv('HOST')
#user = os.getenv('USERNAME')
#password = os.getenv('PASSWORD')
#dbname = os.getenv('DATABASE')
#port = os.getenv('PORT')
#sslmode = os.getenv('SSLMODE')

#nostosdb = psycopg2.connect(
  #  host=os.environ.get('HOST'),
  #  user=os.environ.get('USERNAME'),
  #  password=os.environ.get('PASSWORD'),
   # dbname=os.environ.get('DATABASE'),
   # port=5432,
    #sslmode="prefer"
#)

#print("HOST:", os.environ.get('HOST'))
#print("USER:", os.environ.get('USERNAME'))
#print("DB:", os.environ.get('DATABASE'))
#print("PORT:", os.environ.get('PORT'))

#nostoscur = nostosdb.cursor()

async def hourly_counter():
        global connected_admins_via_userid
        while(True):
         server_time = datetime.now()
         now = datetime.now()
         trimmed = datetime(now.year, now.month, now.day)
         #values = (trimmed,)
         #nostoscur.execute(sql_requests_for_every_time_of_day,values)
         #row = nostoscur.fetchall()
         async with app['db_pool'].acquire() as conn:
            row = await conn.fetch(sql_requests_for_every_time_of_day, trimmed)
         print(row)
         hours_json = [
        {"slot": s[0], "count": s[1]}
        for s in row
         ]
         for sid in connected_admins_via_userid.values():
             await sio.emit("requests_per_day_time_acceptor",{"hours":hours_json},to=sid)
         count = 0
         while(count < 3600):
            await asyncio.sleep(1)
            count += 1

async def daily_counter():
    global connected_admins_via_userid
    global total_daily_requests
    total_daily_requests = 0;
    async with app['db_pool'].acquire() as conn:
            row = await conn.fetch(sql_average_requests_for_every_time_of_day)
    print(row)
    average_hours_json = [
        {"slot": s[0], "count": s[1]}
        for s in row
    ]
    for sid in connected_admins_via_userid.values():
     await sio.emit("average_requests_per_day_time_acceptor",{"hours":average_hours_json},to=sid)
     count = 0
     while(count < 86400):
            await asyncio.sleep(1)
            count += 1

async def init_daily_counter(app):
    asyncio.create_task(daily_counter())

async def init_hourly_counter(app):
    asyncio.create_task(hourly_counter())

########################################################################################################################################################################



server_time = datetime.now()
total_daily_requests = 0;


valid_rooms = set()
########################################################

# pending requests list
requests_list = [
    
]
request_timestamps = {}
total_requests = 0

#requests_list_semaphore = Semaphore()
requests_list_semaphore = asyncio.Lock()

groom_accepted_requests = {}
user_active_requests = {}

########################################################

########################################################
connected_clients = {}
connected_clients_via_userid = {}

connected_clients_jobs = {}

connected_admins = {}
connected_admins_via_userid = {}


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

break_start = {}

#break in users screen
break_emiter = {}

#for overide
overrider = {}
overrider_for_chat = {}
########################################################

########################################################
#for no dupicates of the accepted list 

accepted_rids = set() #set doesnt permit duplicates
overrided_rid = set()

########################################################

#for attention
attentions_list = [
    
]

async def init_db(app):
    global db_pool, users, grooms, admins, room_list, valid_rooms
    global requests_list,request_timestamps,user_active_requests,groom_accepted_requests
    print("Initializing database connection pool...")
    db_pool = await asyncpg.create_pool(
        host="dpg-d676j98boq4c73fo1vig-a.frankfurt-postgres.render.com",
        user="nostosdb",
        password="czLedw1jFvolK7xiGeMytLmwpy5mZrBO",
        database="nostosdb",
        port=5432,
        min_size=2,
        max_size=50
    )
    app['db_pool'] = db_pool
    print("✅ Database pool created!")

    # --- Load all startup data using the pool ---
    async with db_pool.acquire() as conn:
        # 1. Load users
        user_rows = await conn.fetch("SELECT userid, active FROM users")
        users = [{'id': row['userid'], 'status': 'active' if row['active'] else 'inactive'} for row in user_rows]
        print(f"✅ Loaded {len(users)} users")

        # 2. Load grooms
        groom_rows = await conn.fetch("SELECT groomid, active FROM grooms")
        grooms = [{'id': row['groomid'], 'status': 'active' if row['active'] else 'inactive'} for row in groom_rows]
        print(f"✅ Loaded {len(grooms)} grooms")

        # 3. Load admins
        admin_rows = await conn.fetch("SELECT adminid, active FROM admins")
        admins = [{'id': row['adminid'], 'status': 'active' if row['active'] else 'inactive'} for row in admin_rows]
        print(f"✅ Loaded {len(admins)} admins")

        # 4. Load rooms and priorities
        room_rows = await conn.fetch("SELECT room_num, priority FROM rooms")
        room_list = [(row['room_num'], row['priority']) for row in room_rows]
        valid_rooms = {row['room_num'] for row in room_rows}
        print(f"✅ Loaded {len(room_list)} rooms into memory")

        ###############for the lists#####################
        # 5. Restore today's active requests (not completed, not canceled)
        request_rows = await conn.fetch("""
    SELECT RID, userid, location, roomnumber, task, priority, people, insert_time, groomid
    FROM requests
    WHERE insert_time::date = CURRENT_DATE
      AND completed = false
      AND canceled = false
""")

        for row in request_rows:
          rid = row['rid']
          insert_time = row['insert_time']  # this is a datetime object from asyncpg

    # Reconstruct request_timestamps as "%H:%M" string (matching your locator event)
          request_timestamps[rid] = insert_time.strftime("%H:%M")

    # Reconstruct requests_list entry (matching your locator event structure exactly)
          request = {
        "user": row['userid'],
        "location": row['location'],
        "room_number": row['roomnumber'],
        "task": row['task'],
        "dropdown": row['priority'],   # priority column stores the dropdown value
        "counter": row['people'],      # people column stores the counter value
        "time": int(insert_time.timestamp()),  # stored as unix timestamp int
        "elapsed": int((datetime.now() - insert_time).total_seconds()),  # real elapsed time
        "accepted": row['groomid'] is not None,  # if groomid is set, it was accepted
        "RID": rid,
        "timebool": True,
    }
          requests_list.append(request)

          user_request = {
    "user": row['userid'],
    "location": row['location'],
    "room_number": row['roomnumber'],
    "task": row['task'],
    "dropdown": row['priority'],
    "counter": row['people'],
    "time": insert_time.strftime("%H:%M"),
    "accepted": row['groomid'] is not None,
    "RID": rid,
    "timebool": True,
}

          uid = row['userid']
          if uid not in user_active_requests:
             user_active_requests[uid] = []
          user_active_requests[uid].append(user_request)

          if row['groomid'] is not None:
            accepted_rids.add(rid)
            overrider[rid] = row['groomid']
            if row['groomid'] not in groom_accepted_requests:
               groom_accepted_requests[row['groomid']] = []
    
    # Match the shape from delivery event exactly
            groom_request = {
        "userId": row['userid'],
        "location": row['location'],
        "room_number": row['roomnumber'],
        "task": row['task'],
        "dropdown": row['priority'],
        "counter": row['people'],
        "time": insert_time.strftime("%H:%M"),
        "accepted": True,
        "index": None,   # no index on restore, client should handle None
        "RID": rid,
    }
            groom_accepted_requests[row['groomid']].append(groom_request)

    # Restore accepted_rids if a groom had accepted it
          if row['groomid'] is not None:
             accepted_rids.add(rid)
        # Restore overrider map
             overrider[rid] = row['groomid']
        # Restore groom_accepted_requests
             if row['groomid'] not in groom_accepted_requests:
                groom_accepted_requests[row['groomid']] = []
             groom_accepted_requests[row['groomid']].append(request)

# Sort the restored list the same way new requests get sorted
        requests_list = await SortRequestsList(requests_list)

# Restore user_active_requests
        for req in requests_list:
          uid = req["user"]
          if uid not in user_active_requests:
             user_active_requests[uid] = []
          user_active_requests[uid].append(req)

        print(f"✅ Restored {len(requests_list)} active requests from today")
        ##########################################################################
        

        ##########################################################################
        





# Add the signal to aiohttp

async def close_db(app):
    global db_pool
    if db_pool:
        await db_pool.close()
        print("Database pool closed!")



sio = socketio.AsyncServer(
    cors_allowed_origins='*',  
    async_mode='aiohttp',       
    transports=['websocket']    
)
app = web.Application()
app.on_startup.append(init_db)
app.on_startup.append(init_daily_counter)
app.on_startup.append(init_hourly_counter)
app.on_cleanup.append(close_db)
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

def create_token(user_id):
    payload = {
        "id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours = 12)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        print("[AUTH] Token expired")
        return -2
    except jwt.InvalidTokenError:
        print("[AUTH] Invalid token")
        return -1

def get_verified_user(sid, data):
    token = data.get("token")
    if not token:
        return None
    payload = verify_token(token)
    if payload == -1 or payload == -2:
        return payload
    user_id = payload["id"]
    if connected_clients.get(sid) != user_id:
        return None
    print("[SECURITY CLEARANCE ✅]")
    return user_id


print(ph.hash(""))
JWT_SECRET = "testing"


@sio.event
async def login(sid, data):
    user_id = data.get("id") #get the user id
    reconnect_singal = data.get("reconnect")
    password = data.get("password")
    

    #stored_hash = "$2b$12$yCr0ND6pQywR5vDR1IhWtOBkiCxpfp9iFFYlxocKXyNa8RqXF7JP2"
    #print(bcrypt.checkpw(password.encode(), stored_hash.encode()))

    if not user_id or not password:
        await sio.emit('login_response', {"success": False}, to=sid)
        return

    old_sid = None #at start the user has no sid unless we find out he is in the the client list already

    for sid_, uid in connected_clients.items(): #try to find the user id in the connected client list and if you do take the sid to old sid variable
        if uid == user_id:
            old_sid = sid_ #we will use this in the client list
            break

    if old_sid: # if old sid is changed mark reconnection and remove the sid for the current user in the connected client list to 
        print(f"User {user_id} reconnected! Old SID: {old_sid}, New SID: {sid}")
        connected_clients.pop(old_sid)
        connected_clients_jobs.pop(old_sid)
    else:
        for sid_,uid in connected_admins.items():
         if uid == user_id:
          sid_ = sid
        if old_sid:
          connected_admins.pop(old_sid)

   
    if user_id in connected_admins.values():
        print("Admin Reconnected") 
        async with app['db_pool'].acquire() as conn:
         sql_user = await conn.fetchrow("SELECT userid, active,password FROM admins WHERE userid = $1", user_id)
        print(f"[HASH LENGTH]: {len(sql_user['password'])}")
        print(f"[COMPARISON]: {password} - {sql_user['password']}")
        if not await check_password(password, sql_user['password']):
            await sio.emit('login_response', {"success": False}, to=sid)
            return#search again for the user id only this time in the user list
        token = data.get("token")
        print(token)
        if token:
         payload = verify_token(token)
         if payload == -1:
           #await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
           token = create_token(user_id)
           print(token)
         if payload == -2:
           await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
           #token = create_token(user_id)
           print(token)
           return
        connected_admins[sid] = user_id  #change the sid for the current user since it changed and we already deleted the opd one earlier
        connected_admins_via_userid[user_id] = sid
        connected_clients_jobs[sid] = "admin"
        mode[user_id] = "AdminLogin"
        await sio.enter_room(sid, "users_pool")
        await sio.enter_room(sid, "grooms_pool")
        await sio.emit("Admin_Login",{"success": True,"id":user_id,"token":token},to=sid)



    elif any(use['id'] == user_id for use in connected_users): #search again for the user id only this time in the user list
        async with app['db_pool'].acquire() as conn:
         sql_user = await conn.fetchrow("SELECT userid, active,password_hash FROM users WHERE userid = $1", user_id)
        print(f"[HASH LENGTH]: {len(sql_user['password_hash'])}")
        print(f"[COMPARISON]: {password} - {sql_user['password_hash']}")
        if not await check_password(password, sql_user['password_hash']):
            await sio.emit('login_response', {"success": False}, to=sid)
            return#search again for the user id only this time in the user list
        token = data.get("token")
        print(token)
        if token:
         payload = verify_token(token)
         if payload == -1:
           #await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
           token = create_token(user_id)
           print(token)
         if payload == -2:
           await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
           #token = create_token(user_id)
           print(token)
           return
        await sio.emit('amiin', {"iamin": True}, to=sid) #if found emit something to the app telling that the user is aleady in
        print("User Reconnected") #mark reconection again for debugging purposes
        #sio.emit('login_response', {"success": True, "id": user_id, "job": "user","recon":True,"mode":mode[user_id]}, to=sid) #emit standart login message that allows the user to move forward to the app
        connected_clients[sid] = user_id  #change the sid for the current user since it changed and we already deleted the opd one earlier
        connected_clients_via_userid[user_id] = sid
        connected_clients_jobs[sid] = "user"
        #mode[user_id] = data.get("mode")
        await sio.enter_room(sid, "users_pool")
        await mode_handler(user_id,sid,reconnect_singal,"user",token)





        ############################ EXACT SAME THING FOR GROOMS AND CONNECTED_GROOM LIST ############################
    elif any(groo['id'] == user_id for groo in connected_grooms):
        async with app['db_pool'].acquire() as conn:
         sql_groom = await conn.fetchrow("SELECT groomid, active,password_hash FROM grooms WHERE groomid = $1", user_id)
        print(f"[HASH LENGTH]: {len(sql_groom['password_hash'])}")
        print(f"[COMPARISON]: {password} - {sql_groom['password_hash']}")
        if not await check_password(password, sql_groom['password_hash']):
            await sio.emit('login_response', {"success": False}, to=sid)
            return#search again for the user id only this time in the user list
        token = data.get("token")
        if token:
         payload = verify_token(token)
         if payload == -1:
           #await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
           token = create_token(user_id)
           print(token)
         if payload == -2:
           await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
           #token = create_token(user_id)
           print(token)
           return
        await sio.emit('amiin', {"iaming": True}, to=sid)
        print("Groom Reconnected")
        #sio.emit('login_response', {"success": True, "id": user_id, "job": "groom","recon":True,"mode":mode[user_id]}, to=sid)
        connected_clients[sid] = user_id
        connected_clients_via_userid[user_id] = sid
        connected_clients_jobs[sid] = "groom"
        #mode[user_id] = data.get("mode")
        await sio.enter_room(sid, "grooms_pool")
        print(f"Groom {user_id} re-joined grooms_pool with new SID: {sid}")
        await mode_handler(user_id,sid,reconnect_singal,"groom",token)
    
    

    #if user_id in connected_admins.values(): #search again for the user id only this time in the user list
       #print("Admin Reconnected") #mark reconection again for debugging purposes
        #connected_admins[sid] = user_id  #change the sid for the current user since it changed and we already deleted the opd one earlier
        #connected_admins_via_userid[user_id] = sid
       #await sio.emit("Admin_Login",{"success": True,"id":user_id},to=sid)







    else:


     async with app['db_pool'].acquire() as conn:
      
         sql_user = await conn.fetchrow("SELECT userid, active,password_hash FROM users WHERE userid = $1", user_id)
        
         sql_groom = await conn.fetchrow("SELECT groomid, active,password_hash FROM grooms WHERE groomid = $1", user_id)
        
         sql_admin = await conn.fetchrow("SELECT adminid, active,password FROM admins WHERE adminid = $1", user_id)

     #if any(admin['id'] == user_id and admin['status'] == 'active'for admin in admins):
     if sql_admin and sql_admin['active']:#search for the user id in allowed users list // check if the username is allowed
         print(f"[COMPARISON]: {password} - {sql_admin['password']}")
         print(f"[HASH LENGTH]: {len(sql_admin['password'])}")
         if not await check_password(password, sql_admin['password']):
            await sio.emit('login_response', {"success": False}, to=sid)
            return#search again for the user id only this time in the user list
         print(f"✅ Login success for {user_id}") #if it is mark connecton
         token = create_token(user_id)
         print(token)
         connected_admins[sid] = user_id # add the user id and sid pair to the connected clients list
         connected_admins_via_userid[user_id] = sid
         connected_clients_jobs[sid] = "admin"
         mode[user_id] = "AdminLogin"
         await sio.enter_room(sid, "users_pool")
         await sio.enter_room(sid, "grooms_pool")
         await sio.emit("Admin_Login",{"success": True,"id":user_id,"token":token},to=sid)
        #or (user['id'] == 'benchmarker' and user['status'] == 'active' for user in users)
       ############################ STANDART LOGIN FUNCTIONALITY // IF THE USER/GROOM IS NOT IN THE CONNECTED LISTS ############################
     #elif any(user['id'] == user_id and user['status'] == 'active'for user in users) or (user_id =='benchmarker'):
     elif sql_user and sql_user['active']:#search for the user id in allowed users list // check if the username is allowed
        print(f"[COMPARISON]: {password} - {sql_user['password_hash']}")
        print(f"[HASH LENGTH]: {len(sql_user['password_hash'])}")
        if not await check_password(password, sql_user['password_hash']):
            await sio.emit('login_response', {"success": False}, to=sid)
            return#search again for the user id only this time in the user list
        print(f"✅ Login success for {user_id}") #if it is mark connecton
        token = create_token(user_id)
        print(token)
        connected_users.append({"id": user_id,"page":False,"timebool":False}) #add the user id along with page and timebool parameters to the connected users list
        connected_clients[sid] = user_id # add the user id and sid pair to the connected clients list
        connected_clients_via_userid[user_id] = sid
        connected_clients_jobs[sid] = "user"
        mode[user_id] = "Login"
        await sio.enter_room(sid, "users_pool")
        await sio.emit('login_response', {"success": True, "id": user_id, "job": "user","token":token,"mode":mode[user_id],"recon":False}, to=sid) # emit standart login message that allows the user to move forward to the app


        ############################ EXACT SAME THING FOR GROOMS AND CONNECTED_GROOM LIST ############################
     #elif any(groom['id'] == user_id and groom['status'] == 'active' for groom in grooms) or (user_id == 'pmurans') or (user_id == 'kandreadis'):
     elif sql_groom and sql_groom['active']:
        print(f"[COMPARISON]: {password} - {sql_groom['password_hash']}")
        if not await check_password(password, sql_groom['password_hash']):
            await sio.emit('login_response', {"success": False}, to=sid)
            return#search again for the user id only th
        print(f"✅ Login success for {user_id}")
        token = create_token(user_id)
        connected_grooms.append({"id": user_id})
        active_grooms.append(user_id)
        connected_clients[sid] = user_id
        connected_clients_via_userid[user_id] = sid
        connected_clients_jobs[sid] = "groom"
        mode[user_id] = "Login"
        await sio.enter_room(sid, "grooms_pool")
        print(f"Groom {user_id} joined the live board.")
        await sio.emit('login_response', {"success": True, "id": user_id, "job": "groom","token":token,"mode":mode[user_id],"recon":False}, to=sid)
        #groom_accepted_requests[user_id] = []
     #elif any(admin['id'] == user_id and admin['status'] == 'active'for admin in admins): #search for the user id in allowed users list // check if the username is allowed
         #print(f"✅ Login success for {user_id}") #if it is mark connecton
         #connected_admins[sid] = user_id # add the user id and sid pair to the connected clients list
         #connected_admins_via_userid[user_id] = sid
         #mode[user_id] = "AdminLogin"
         #await sio.emit("Admin_Login",{"success": True,"id":user_id},to=sid)
     elif data.get("token"):
         if payload == -1:
           await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
           return
         if payload == -2:
           await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
           return
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
    global total_requests
    global room_list
    global total_daily_requests

    ###get all the app sends//info about the request###
    location = data.get("location")
    room_number = data.get("Room Number")
    task = data.get("Task")
    dropdown = data.get("DropDown")
    counter = data.get("Counter")
    RID = data.get("RID")


    found = False

    for room, priority in room_list:
     if room == room_number:
        print(f"Room {room} has priority {priority}")
        found = True
        
        
    if found == False:
         await sio.emit("room_return",{"response":2,"priority":priority},to=sid)
         return

    
    timestamp = datetime.now().strftime("%H:%M")
    request_timestamps[RID] = timestamp
    print(f"[TIME] {timestamp}")

    now = datetime.now() 
    trimmed = datetime(now.year, now.month, now.day, now.hour, now.minute)


    #user_id = connected_clients[sid] # get the username cause we will need it from the connected_clients list since we have the sid
    user_id = get_verified_user(sid, data)
    if user_id is None:
        print(f"[SECURITY] Unauthorized locator from {sid}")
        return  # no token at all
    if user_id == -2:
        print(f"[SECURITY EXPIRED TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
        return
    if user_id == -1:
        print(f"[SECURITY INVALID TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
        return
    
    if user_id and is_rate_limited(user_id, limit=3, window=1):
        print(f"[SECURITY] Rate limited user {user_id} on locator event.")
        return

    if len(str(room_number)) > 5:
        print(f"[SECURITY] Payload too large from sid {sid}")
        await sio.emit("room_return",{"response":2,"priority":priority},to=sid)
        return

    
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
        
     
       

   # nostoscur.execute("""
    #INSERT INTO requests (
      #  RID, userid, groomid, insert_time,accept_time, finish_time,
      #  people, task, roomnumber, priority, overrided_by,location
    #) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
#""", (
   # RID, user_id, None, trimmed, None, None, 
   # counter, task, room_number, dropdown, None,location
#))
    #nostosdb.commit()
    

    async with db_pool.acquire() as conn:
        await conn.execute("""
    INSERT INTO requests (
        RID, userid, groomid, insert_time,accept_time, finish_time,
        people, task, roomnumber, priority, overrided_by,location
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,$12)
""", 

    RID, user_id, None, trimmed, None, None, 
    counter, task, room_number, dropdown, None,location
)
     
    asyncio.create_task(time_counter(RID)) #spawn a counter for this request// create an cpu-load friendly *thread* that is responsible for running the counter for the current user
    #eventlet.spawn(request_sender,sid,user_id)
    
    total_daily_requests+=1
    total_requests+=1
    asyncio.create_task(broadcast_user_active_requests(user_id, sid))
    asyncio.create_task(broadcast_requests(sid))
    asyncio.create_task(broadcast_timestamps())
    asyncio.create_task(send_total_requests())
    asyncio.create_task(admin_total_daily_requests_sender())
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
    #user_id = data.get("user_id")
    user_id = get_verified_user(sid, data)
    if user_id is None:
        print(f"[SECURITY] Unauthorized locator from {sid}")
        return  # no token at all
    if user_id == -2:
        print(f"[SECURITY EXPIRED TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
        return
    if user_id == -1:
        print(f"[SECURITY INVALID TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
        return
    mode = data.get("mode")
    asyncio.create_task(broadcast_user_active_requests(user_id, sid))

@sio.event 
async def delete_request(sid,data):
    global total_requests
    global total_daily_requests
    RID = data.get("RID")
    #user_id = data.get("user_id")
    user_id = get_verified_user(sid, data)
    if not user_id:
        print(f"[SECURITY] Unauthorized locator from {sid}")
        return

    actual_user_id = connected_clients.get(sid)

    print(f"[DELETE] User {user_id} requested delete for RID {RID}")

    req = next((r for r in requests_list if r["RID"] == RID), None)
    
    # 3. If the request exists, make sure the person deleting it OWNS it (or is an admin)
    if req and req["user"] != actual_user_id and sid not in connected_admins:
        print(f"[SECURITY] User {actual_user_id} tried to delete RID {RID} which isn't theirs!")
        return

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


    #delete_request_sql = """
    #UPDATE messages
    #SET canceled = 1
    #WHERE RID = %s
    #AND DATE(insert_datetime) = CURDATE()
    #"""

    async with app['db_pool'].acquire() as conn:
        await conn.execute("""
    UPDATE messages
    SET canceled = true
    WHERE RID = $1
    AND DATE(insert_datetime) =  CURRENT_DATE
    """,RID)

        await conn.execute("""
    UPDATE requests
    SET canceled = true  
    WHERE RID = $1
      AND DATE(insert_time) = CURRENT_DATE
""", RID)

    #nostoscur.execute
   
   # values =(RID,)
   # nostoscur.execute(delete_request_sql, values)
    #nostosdb.commit()
    # broadcast updates
    total_requests = total_requests - 1
    asyncio.create_task(broadcast_requests(sid))
    asyncio.create_task(broadcast_accepted_requests(user_id,-1))
    asyncio.create_task(broadcast_user_active_requests(user_id, sid))
    asyncio.create_task(send_total_requests())
    asyncio.create_task(chat_updater_for_up_strech())
    asyncio.create_task(admin_total_daily_requests_sender())
    
    print(f"[DELETE] RID {RID} fully removed")



####################################################################################
   

####################################################################################
@sio.event
async def delivery(sid, data):
    #groom_id = data.get("groom")
    action = data.get("action")

    groom_id= get_verified_user(sid, data)
    if groom_id is None:
        print(f"[SECURITY] Unauthorized locator from {sid}")
        return  # no token at all
    if groom_id == -2:
        print(f"[SECURITY EXPIRED TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
        return
    if groom_id == -1:
        print(f"[SECURITY INVALID TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
        return

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
       
       now = datetime.now()
       trimmed = datetime(now.year, now.month, now.day, now.hour, now.minute)
        
       now2 = datetime.now()
       trimmed2 = datetime(now2.year, now2.month, now2.day)

       async with app['db_pool'].acquire() as conn:
        await conn.execute("""
    UPDATE requests
    SET accept_time = $1,
        groomid = $2
    WHERE RID = $3
     AND insert_time::date = $4
""", trimmed, groom_id, RID,trimmed2)

       #nostoscur.execute()
       #nostosdb.commit()
       #AND DATE(insert_time) = CURRENT_DATE
       print(trimmed)
       print(RID)
       print(accepted_rids)
       #print("[Rows updated]:", nostoscur.rowcount) 

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
        now2 = datetime.now()
        trimmed2 = datetime(now2.year, now2.month, now2.day)

        async with app['db_pool'].acquire() as conn:
         await conn.execute("""
    UPDATE requests
    SET overrided_by = $1
    WHERE RID = $2
      AND insert_time::date = $3
""", groom_id, RID, trimmed2)

        #nostoscur.execute()
     #AND DATE(insert_time) = CURRENT_DATE
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
    #groom_id = data.get("groom")
    groom_id= get_verified_user(sid, data)
    if groom_id is None:
        print(f"[SECURITY] Unauthorized locator from {sid}")
        return  # no token at all
    if groom_id == -2:
        print(f"[SECURITY EXPIRED TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
        return
    if groom_id == -1:
        print(f"[SECURITY INVALID TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
        return

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
    asyncio.create_task(chat_updater_for_up_strech())
    now2 = datetime.now()
    trimmed2 = datetime(now2.year, now2.month, now2.day)

    async with app['db_pool'].acquire() as conn:
        await conn.execute("""
    UPDATE messages
    SET canceled = true
    WHERE RID = $1
    AND insert_datetime::date = $2 
    """,RID,trimmed2)
    #delete_request_sql2 = 


        await conn.execute("""
    UPDATE requests
    SET groomid = NULL,
        accept_time = NULL
    WHERE RID = $1
    AND insert_time::date = $2 
""", RID,trimmed2)
    #nostoscur.execute()
  
    #values =(RID,trimmed2)
    #nostoscur.execute(delete_request_sql2, values)
    #nostosdb.commit()

@sio.event
async def Arrived(sid, data):
    
    global total_requests
    global total_daily_requests

    #groom_id = data.get("groom")
    groom_id= get_verified_user(sid, data)
    if groom_id is None:
        print(f"[SECURITY] Unauthorized locator from {sid}")
        return  # no token at all
    if groom_id == -2:
        print(f"[SECURITY EXPIRED TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
        return
    if groom_id == -1:
        print(f"[SECURITY INVALID TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
        return
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

    
    #update_sql = """
    #UPDATE messages
    #SET fullfilled = 1
    #WHERE RID = %s
    #AND DATE(insert_datetime) = CURDATE()
    #"""
   
    total_requests = total_requests - 1
    asyncio.create_task(broadcast_requests(sid))
    asyncio.create_task(broadcast_accepted_requests(groom_id,sid))
    asyncio.create_task(broadcast_user_active_requests(user_id,target_sid))
    asyncio.create_task(broadcast_timestamps())
    asyncio.create_task(send_total_requests())
    asyncio.create_task(chat_updater_for_up_strech())
    asyncio.create_task(admin_total_daily_requests_sender())
    asyncio.create_task(late_requests_for_today_sender())  
    now = datetime.now()
    trimmed = datetime(now.year, now.month, now.day, now.hour, now.minute)

    now2 = datetime.now()
    trimmed2 = datetime(now2.year, now2.month, now2.day)


    async with app['db_pool'].acquire() as conn:
        await conn.execute("""
    UPDATE messages
    SET fullfilled = true
    WHERE RID = $1
    AND insert_datetime::date = $2  
    """,RID,trimmed2)
    #values =(RID,trimmed2)
    #update_sql = 
#AND DATE(insert_datetime) = CURRENT_DATE

        await conn.execute("""
    UPDATE requests
    SET finish_time = $1,
        completed = true
    WHERE RID = $2
      AND insert_time::date = $3  
""", trimmed, RID, trimmed2)
    #nostoscur.execute()
     #AND DATE(insert_time) = CURRENT_DATE
    #nostoscur.execute(update_sql, values)
    #nostosdb.commit()

    ####################################################################################

    ####################################################################################
@sio.event
async def Break(sid, data):
   reason = data.get("reason")
   #user_id = data.get("userid")

   user_id= get_verified_user(sid, data)
   if user_id is None:
        print(f"[SECURITY] Unauthorized locator from {sid}")
        return  # no token at all
   if user_id == -2:
        print(f"[SECURITY EXPIRED TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
        return
   if user_id == -1:
        print(f"[SECURITY INVALID TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
        return


   if(reason != "stop"):
     print("user",user_id," takes a break with reason: ",reason)
     active_grooms.remove(user_id) 
     breaking_grooms.append(user_id)
     await sio.emit("break_confirmation",{"confirmation":True},to=connected_clients_via_userid[user_id])
     break_timers[user_id] = True
     thread = asyncio.create_task(break_clock(user_id))
     now = datetime.now()
     trimmed = datetime(now.year, now.month, now.day, now.hour, now.minute,now.second)
     break_start[user_id] = trimmed 

     async with app['db_pool'].acquire() as conn:
        await conn.execute("""
    INSERT INTO breaks (groomid, begining, finish)
    VALUES ($1, $2, $3)
""", user_id, trimmed, None)
     #nostoscur.execute()
     #nostosdb.commit()
        #start a timer with a function
   else:
       break_timers[user_id] = False
       active_grooms.append(user_id)
       breaking_grooms.remove(user_id)

       now2 = datetime.now()
       trimmed = datetime(now2.year, now2.month, now2.day, now2.hour, now2.minute,now2.second)
       

       async with app['db_pool'].acquire() as conn:
        await conn.execute("""
    UPDATE breaks
    SET finish = $1
    WHERE groomid = $2
      AND begining = $3
""", trimmed, user_id, break_start[user_id])
       #nostoscur.execute()
       #nostosdb.commit()
       #break_start.pop(user_id)

 

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
 asyncio.create_task(broadcast_accepted_requests(user_id,sid))###################################################################################################

            
 #####$$$$$$ THIS SENDS THE UPDATE MESSAGES TO EVERYONE AND IT NEEDS TO BE MADE SO IT SENDS THE UPDATES ONLY TO USERS $$$$$$#####
 
#sql_change_attention = 
@sio.event 
async def AttentionAddition(sid,data):

    user_id= get_verified_user(sid, data)
    if user_id is None:
        print(f"[SECURITY] Unauthorized locator from {sid}")
        return  # no token at all
    if user_id == -2:
        print(f"[SECURITY EXPIRED TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
        return
    if user_id == -1:
        print(f"[SECURITY INVALID TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
        return

    addition = data.get("addition") 
    level = addition["level"]
    room_num = addition["number"]
    priority = await configure_priority(level)
    #values = (priority,room_num)
    async with app['db_pool'].acquire() as conn:
        await conn.execute("""
 UPDATE rooms
 SET priority = $1
 WHERE room_num = $2
 """,priority,room_num)

    #nostoscur.execute(sql_change_attention,values)
    #nostosdb.commit()
    attentions_list.append(addition)
    print(attentions_list)
    await sio.emit("AttentionList", {
        "list": attentions_list
    },room="users_pool")

    

@sio.event
async def AttentionRemoval(sid,data):

    user_id= get_verified_user(sid, data)
    if user_id is None:
        print(f"[SECURITY] Unauthorized locator from {sid}")
        return  # no token at all
    if user_id == -2:
        print(f"[SECURITY EXPIRED TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
        return
    if user_id == -1:
        print(f"[SECURITY INVALID TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
        return


    index = data.get("index")
    number = attentions_list[0]['number']
    #values = (number,0)
    async with app['db_pool'].acquire() as conn:
        await conn.execute("""
 UPDATE rooms
 SET priority = $1
 WHERE room_num = $2
 """,number,0)
    #nostoscur.execute(sql_change_attention,values)
    #nostosdb.commit()
    attentions_list.pop(index)
    print(attentions_list)
    await sio.emit("AttentionList", {
        "list": attentions_list
    },room="users_pool")


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


async def mode_handler(user_id,sid,recon,job,token):
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
        case "ChatPage":
            await sio.emit("Mode Handlder", {"mode":mode_handled})
            

    else:
            isb = False
            if user_id in breaking_grooms:
                isb = True 

            print(f"[!!!]{isb}")
            await sio.emit('login_response', {"success": True, "id": user_id,"token":token, "job": job,"recon":True,"mode":mode_handled,"is_breaking":isb}, to=sid) 
            #broadcast_timestamps()

async def broadcast_requests(sid):
   print("get ready")
   print(sid)
   #print(connected_users)
   #print(connected_grooms)
   #print(connected_clients)
   #for i in range(5):
     #sio.emit("Board", requests_list,to=sid)
   #await sio.emit("Board", requests_list)
   await sio.emit("Board", requests_list, room="grooms_pool")
   await asyncio.sleep(1)

   


async def broadcast_timestamps():
    #for i in range(5):
        #for rid, ts in request_timestamps.items():
        #for rid, ts in list(request_timestamps.items()):
        snapshot = request_timestamps.copy()
        for rid, ts in snapshot.items():
            await sio.emit("timestamp", {"RID": rid, "timestamp": ts},room="grooms_pool")
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
   # for i in range(5):
      #sio.emit("Board", requests_list,to=sid)
      await sio.emit("accepted_requests",groom_accepted_requests[groom_id],to=sid)
      await asyncio.sleep(1)
   else:
      #for target_sid, job in connected_clients_jobs.items():
        # if job != "groom":
         #   continue

         #groom_id = connected_clients[target_sid]
        # if groom_id not in groom_accepted_requests:
         #   groom_accepted_requests[groom_id] = []
         await sio.emit("accepted_requests", groom_accepted_requests[groom_id],room="grooms_pool")






    


async def broadcast_user_active_requests(user_id,sid):
   print("get ready")
   print(sid)
   #print(connected_users)
   #print(connected_grooms)
   #print(connected_clients)
   if user_id not in user_active_requests:
    user_active_requests[user_id] = []
   #for i in range(5):
     #sio.emit("Board", requests_list,to=sid)
   await sio.emit("user_active_requests",user_active_requests[user_id],to=sid)
   await asyncio.sleep(1)

####################################################################################
async def time_counter(RID):
    sent = False
    while True:
        # find the request by RID
        req = next((r for r in requests_list if r["RID"] == RID), None)
        if not req or not req["timebool"]:
            break
        await asyncio.sleep(1)
        req["elapsed"] += 1
        #if req["elapsed"] > 15 and sent == False:
        #    print("[request late]")
        #    asyncio.create_task(late_requests_for_today_sender()) 
        #    sent = True







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
"""users = [
    {'id': f'user00{i}', 'status': 'active'} for i in range(1, 11)
]
print("✅ Loaded users:", users)

grooms = [
    {'id': f'groom00{i}', 'status': 'active'} for i in range(1, 11)
]
print("✅ Loaded grooms:", grooms)

grooms.append({'id':'pmurans','status':'active'})
grooms.append({'id':'kandreadis','status':'active'})
users.append({'id':'benchmarker','status':'active'})"""

#nostoscur.execute("SELECT userid, active FROM users")
#users = [{'id': row[0], 'status': 'active' if row[1] else 'inactive'} for row in nostoscur.fetchall()]
#print("✅ Loaded users:", users)

# --- Load grooms ---
#nostoscur.execute("SELECT groomid, active FROM grooms")
#grooms = [{'id': row[0], 'status': 'active' if row[1] else 'inactive'} for row in nostoscur.fetchall()]
#print("✅ Loaded grooms:", grooms)

#nostoscur.execute("SELECT adminid, active FROM admins")
#admins = [{'id': row[0], 'status': 'active' if row[1] else 'inactive'} for row in nostoscur.fetchall()]
#print("✅ Loaded admins:", admins)



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






@sio.event 
async def utils(sid,data):
    user_id = data.get("user_id")
    sid =  connected_clients_via_userid[user_id]
    await system_monitor(sid)

@sio.event 
async def Benchmarker(sid,data):
    global requests_list
    global request_timestamps
    global groom_accepted_requests
    global user_active_requests
    global accepted_rids
    global overrided_rid
    global total_requests
    total_requests = 0

    user_id= data.get("user_id")    
    requests_list.clear()
    request_timestamps.clear()
    groom_accepted_requests.clear()
    user_active_requests.clear()
    user_active_requests[user_id] = []
    accepted_rids.clear()
    overrided_rid.clear()

    asyncio.create_task(broadcast_requests(sid))
    asyncio.create_task(broadcast_timestamps())
    asyncio.create_task(send_total_requests())


async def send_total_requests():
  global total_requests 
  print(total_requests)
  sid = connected_clients_via_userid["benchmarker"]
  await sio.emit("reqs",{"reqs":total_requests},to=sid)

async def system_monitor(sid):
    process = psutil.Process(os.getpid())

    #cpu = process.cpu_percent(interval=1)
    #mem = process.memory_info().rss / (1024 * 1024)  # MB
    #total_mem = psutil.virtual_memory().percent

    #cpu = psutil.cpu_percent(interval=None)
    #mem = process.memory_info().rss / (1024 * 1024)
    #total_mem = psutil.virtual_memory().percent
    process = psutil.Process()
    process.cpu_percent(interval=None)  
    await asyncio.sleep(0.5)           
    cpu = process.cpu_percent(interval=None)
    mem = process.memory_info().rss / (1024 * 1024)
    total_mem = psutil.virtual_memory().percent


    await sio.emit("benchmarks",{"cpu":cpu,"ram":mem,"total_ram":total_mem},to=sid)

 
     
@sio.event
async def ping(sid, data):
    #print("[+]Pinged")
    await sio.emit("pong", {
        "pong": data.get("ping")
    }, to=sid)


@sio.event
async def server_down(sid,data):
    user_id = data.get("id")
    mode = data.get("mode")
    reconnect = data.get("reconnect")
    job = data.get("job")

    if job == "user":
        connected_users.append({"id": user_id,"page":False,"timebool":False}) #add the user id along with page and timebool parameters to the connected users list
        connected_clients[sid] = user_id # add the user id and sid pair to the connected clients list
        connected_clients_via_userid[user_id] = sid
        connected_clients_jobs[sid] = "user"
        mode[user_id] = "Login"
    elif job == "groom":
        connected_grooms.append({"id": user_id})
        active_grooms.append(user_id)
        connected_clients[sid] = user_id
        connected_clients_via_userid[user_id] = sid
        connected_clients_jobs[sid] = "groom"
        mode[user_id] = "Login"


insert_message_sql = "INSERT INTO messages (RID, name, message, insert_datetime) VALUES (%s, %s, %s, %s)"
#select_messages_page_sql = """
#SELECT id, RID, name, message
#FROM messages
#ORDER BY id DESC
#LIMIT %s OFFSET %s
#"""

#select_messages_page_sql = """
#SELECT id, RID, name, message, fullfilled,canceled,message_deleted
#FROM messages
#ORDER BY id DESC
#LIMIT %s OFFSET %s
#"""

select_messages_page_sql= """SELECT id, RID, name, message, fullfilled, canceled, message_deleted
FROM messages
WHERE name IS NOT NULL
  AND NOT fullfilled 
  AND NOT canceled 
  AND NOT message_deleted 
ORDER BY id DESC
LIMIT %s OFFSET %s"""

update_message_sql = "UPDATE messages SET name = %s WHERE RID = %s"


@sio.event
async def send_message(sid,data):

    user_id= get_verified_user(sid, data)
    if user_id is None:
        print(f"[SECURITY] Unauthorized locator from {sid}")
        return  # no token at all
    if user_id == -2:
        print(f"[SECURITY EXPIRED TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
        return
    if user_id == -1:
        print(f"[SECURITY INVALID TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
        return

    #user_id = data.get("user_id")
    message = data.get("message")
    RID = data.get("RID")


    if not isinstance(message, str) or len(message) > 500:
        print(f"[SECURITY] Invalid message length or type from sid {sid}")
        # Optionally emit an error back to the user
        return


    now = datetime.now()
    trimmed = datetime(now.year, now.month, now.day, now.hour, now.minute)
    print(f"[NEW MESSAGE]: {message}")

    try:
        #values = (RID, user_id, message,trimmed)
        async with app['db_pool'].acquire() as conn:
         await conn.execute("INSERT INTO messages (RID, name, message, insert_datetime) VALUES ($1, $2, $3, $4)",RID,user_id,message,trimmed)
        #nostoscur.execute(insert_message_sql, values)
        #nostosdb.commit()

        # ✅ tell ALL clients to refresh messages
        await sio.emit("refresh_messages")

    except Exception as e:
        print("DB Error:", e)
        


@sio.event
async def get_messages_page(sid, data):

    user_id= get_verified_user(sid, data)
    if user_id is None:
        print(f"[SECURITY] Unauthorized locator from {sid}")
        return  # no token at all
    if user_id == -2:
        print(f"[SECURITY EXPIRED TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
        return
    if user_id == -1:
        print(f"[SECURITY INVALID TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
        return
    
    RID = data.get("RID")
    page = data.get("page", 0)   
    limit = 20
    offset = page * limit
    try:
      
        
        #nostoscur.execute(select_messages_page_sql, (limit, offset))
        async with app['db_pool'].acquire() as conn:
         rows = await conn.fetch("""SELECT id, RID, name, message, fullfilled, canceled, message_deleted
FROM messages
WHERE name IS NOT NULL
  AND NOT fullfilled 
  AND NOT canceled 
  AND message_deleted = $1
ORDER BY id DESC
LIMIT $2 OFFSET $3""",False,limit,offset)
         #rows = nostoscur.fetchall()

        
        messages = []

        for row in rows:
           if row[2] is None or row[4] == 1 or row[5] == 1 or row[6] == 1:
               print("[SKIPPING]")
           else:
            messages.append({
                "id": row[0],
                "RID": row[1],
                "name": row[2],
                "message": row[3]
            })
        print(f"[ALL MESSAGES]: {messages}")
        await sio.emit("messages_page", {
            "page": page,
            "messages": messages
        },room = "grooms_pool")

    except Exception as e:
        print("DB Error:", e)


@sio.on("chat_request_message")
async def chat_request_message(sid, data):

    rid = data["RID"]
    sender = data["sender"]

    await store_request_as_message(rid, sender)

    req = get_request_by_rid(rid)

    if not req:
        print(f"[CHAT REQUEST] RID {rid} not found")
        return

    message = {
        "type": "request",
        "RID": rid,
        "sender": sender,
        "location": req["location"],
        "room": req["room_number"],
        "task": req["task"],
        "accepted": req["accepted"]
    }

    #await sio.emit("chat_message", message)
    asyncio.create_task(broadcast_requests(sid))
    asyncio.create_task(broadcast_timestamps())
    asyncio.create_task(chat_updater_for_up_strech())
    #asyncio.create_task(broadcast_user_active_requests(user_id,target_sid))
    await sio.emit("refresh_messages")


def get_request_by_rid(rid):
    for req in requests_list:
        if req["RID"] == rid:
            return req
    return None

async def store_request_as_message(rid, user_id):
    try:
        # Name is "req" so we know it's a request type
        now = datetime.now()
        #values = (rid, user_id, str(rid),now)  # message can just store the RID for reference
        async with app['db_pool'].acquire() as conn:
         await conn.execute("INSERT INTO messages (RID, name, message, insert_datetime) VALUES ($1, $2, $3, $4)",rid,user_id,str(rid),now)
        #nostoscur.execute(insert_message_sql, values)
        #nostosdb.commit()
        print(f"[DB] Stored request RID {rid} as message")
    except Exception as e:
        print("DB Error storing request:", e)

@sio.event
async def update_sql_req(sid,data):

    RID = data.get("RID")
    user_id = data.get("user_id")
    action = data.get("action")
    if action == 0:
      overrider_for_chat[RID] = user_id
    else:
     
     overrided = overrider_for_chat[RID]
     target_sid = connected_clients_via_userid[overrided]
     values = (user_id, RID)  
     async with app['db_pool'].acquire() as conn:
         await conn.execute("UPDATE messages SET name = $1 WHERE RID = $2",user_id,RID)
     #nostoscur.execute(update_message_sql, values)
     #nostosdb.commit()
     #print(f"overrided_groom_ {overrided_groom_}")
     await sio.emit("chat_override",{"override":True},to=target_sid)
     overrider_for_chat[RID] = user_id
    
@sio.event
async def BroadCaster(sid,data):

    groom_id = data.get("groom_id")


    asyncio.create_task(broadcast_requests(sid))
    asyncio.create_task(broadcast_accepted_requests(groom_id,sid))
    #asyncio.create_task(broadcast_user_active_requests(user_id,target_sid))
    asyncio.create_task(broadcast_timestamps())
    #asyncio.create_task(send_total_requests())



#delete_request_from_chat = """
    #UPDATE messages
    #SET message_deleted = 1
    #WHERE RID = %s
    #AND DATE(insert_datetime) = CURDATE()
    #"""

#delete_message_from_chat = """
  #  UPDATE messages
  #  SET message_deleted = 1
   # WHERE id = %s
   # AND DATE(insert_datetime) = CURDATE()
    #"""

#edit_message_from_chat = 
   # UPDATE messages
   # SET message = %s, 
   #     message_edited = 1
   # WHERE id = %s
   # AND DATE(insert_datetime) = CURDATE()
   # """

delete_request_from_chat = """
    UPDATE messages
    SET message_deleted = true
    WHERE RID = $1
    AND DATE(insert_datetime) = CURRENT_DATE
"""

delete_message_from_chat = """
    UPDATE messages
    SET message_deleted = true
    WHERE id = $1
    AND DATE(insert_datetime) = CURRENT_DATE
"""

edit_message_from_chat = """
    UPDATE messages
    SET message = $1, 
        message_edited = true
    WHERE id = $2
    AND DATE(insert_datetime) = CURRENT_DATE
"""

@sio.event 
async def delete_request_message(sid, data):

    user_id= get_verified_user(sid, data)
    if user_id is None:
        print(f"[SECURITY] Unauthorized locator from {sid}")
        return  # no token at all
    if user_id == -2:
        print(f"[SECURITY EXPIRED TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
        return
    if user_id == -1:
        print(f"[SECURITY INVALID TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
        return

    RID = data.get("RID")   
    # Use pool.execute for a single UPDATE statement
    async with app['db_pool'].acquire() as conn:
        await conn.execute(delete_request_from_chat, RID)       
    await sio.emit("refresh_messages")

@sio.event 
async def delete_message(sid, data):
    user_id= get_verified_user(sid, data)
    if user_id is None:
        print(f"[SECURITY] Unauthorized locator from {sid}")
        return  # no token at all
    if user_id == -2:
        print(f"[SECURITY EXPIRED TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
        return
    if user_id == -1:
        print(f"[SECURITY INVALID TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
        return
    message_id = data.get("id")
    async with app['db_pool'].acquire() as conn:
        await conn.execute(delete_message_from_chat, message_id)     
    await sio.emit("refresh_messages")

@sio.event 
async def edit_message(sid, data):
    user_id= get_verified_user(sid, data)
    if user_id is None:
        print(f"[SECURITY] Unauthorized locator from {sid}")
        return  # no token at all
    if user_id == -2:
        print(f"[SECURITY EXPIRED TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
        return
    if user_id == -1:
        print(f"[SECURITY INVALID TOKEN] Unauthorized locator from {sid}")
        await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
        return
    message_id = data.get("messageId")
    message_text = data.get("message") 
    # Important: message_text is $1, message_id is $2
    async with app['db_pool'].acquire() as conn:
        await conn.execute(edit_message_from_chat, message_text, message_id)      
    await sio.emit("refresh_messages")

async def chat_updater_for_up_strech():
    await sio.emit("refresh_messages")




@sio.event
async def Logout(sid,data):
    global connected_users
    global connected_grooms
    global connected_clients
    global connected_clients_via_userid
    user_id = data.get("user_id")
    confirm = data.get("signal")
    mode = data.get("mode")
    job = data.get("job")

    await sio.emit("Logout_Confirmation",{"cond":True})

    connected_clients_via_userid.pop(user_id)
    connected_clients.pop(sid)
    print(f"[JOB]: {job}")
    print(f"[USERID]: {user_id}")
    if job == "groom":
     for user in connected_grooms:
      if user['id'] == user_id:
        connected_grooms.remove(user)
        break  # stop after first match

    elif job == "user":
      for user in connected_users:
       if user['id'] == user_id:
        connected_users.remove(user)
        break  # stop after first match

    print(connected_grooms)
    print(connected_users)
    
    

sql_find_admin_password = """
SELECT password FROM admins
WHERE adminid = $1
"""

@sio.event
async def admin_password(sid, data):
    admin_id = data.get("user_id")
    password = data.get("password")   
    # 2. Acquire connection and use fetchrow()
    #async with app['db_pool'].acquire() as conn:
        #row = await conn.fetchrow(sql_find_admin_password, admin_id)
    # 3. Check if row exists (None means no user found)
    #if row is None:
        #
       # return
    async with app['db_pool'].acquire() as conn:
        sql_admin = await conn.fetchrow("SELECT userid, active,password FROM admins WHERE userid = $1", admin_id)
        print(f"[HASH LENGTH]: {len(sql_admin['password'])}")
        print(f"[COMPARISON]: {password} - {sql_admin['password']}")
        if not await check_password(password, sql_admin['password']):
            await sio.emit("Connected", {"success": False}, to=sid)
            return
    token = data.get("token")
    print(token)
    
    if token:
     payload = verify_token(token)
     if payload == -1:
           #await sio.emit('login_response', {"success": False, "reason": "invalid"}, to=sid)
           await sio.emit("Connected", {"success": False}, to=sid)
           print(token)
           return
     if payload == -2:
           #await sio.emit('login_response', {"success": False, "reason": "expired"}, to=sid)
           await sio.emit("Connected", {"success": False}, to=sid)
           print(token)
           return
        #search again for the user id only this time in the user list
    # row works like a dictionary or a list
    #db_password = row['password']  

     connected_clients[sid] = admin_id
     connected_clients_via_userid[admin_id] = sid
     connected_users.append({"id": admin_id, "page": False, "timebool": False})
     connected_grooms.append({"id": admin_id})
     await sio.emit("Connected", {"success": True}, to=sid)
     return
    await sio.emit("Connected", {"success": False}, to=sid)
 
       


sql_return_all_valid_rooms = """
SELECT room_num, priority FROM rooms
"""
sql_return_priority_from_room = """
SELECT priority FROM rooms
WHERE room_num = $1
"""
#async def return_rooms(user_id,sid):
#nostoscur.execute(sql_return_all_valid_rooms)
#row = nostoscur.fetchall()   
#room_list = row
#print(room_list)
#valid_rooms = {room for room, _ in room_list} 
#print(valid_rooms)

async def return_rooms(user_id, room_to_find):
    global room_list
    global valid_rooms
    secondary_list = []
    
    # 2. Acquire connection and use fetchval() 
    # fetchval() is perfect here because you only want the 'priority' column
    async with app['db_pool'].acquire() as conn:
        level = await conn.fetchval(sql_return_priority_from_room, room_to_find)

    # In asyncpg, if no row is found, fetchval returns None
    print(f"Room Level: {level}")

    sid = connected_clients_via_userid.get(user_id)
    if sid is None:
        return

    if level is not None:
        print(f"Room {room_to_find} has priority {level}")
        pr = await configure_priority_reverse(level)
        print(f"which is {pr}")

        await sio.emit("room_return", {"response": 1, "priority": pr}, to=sid)
        return
    
    # If room was not found
    await sio.emit("room_return", {"response": 0, "priority": 0}, to=sid)
 
@sio.event
async def room_check(sid,data):
    
    room = data.get("room")
    user_id = data.get("user_id")
    print(room)

    if room == 67:
     await return_rooms(user_id,1001)
    else:
     await return_rooms(user_id,room)


async def propose_room(room_to_find):
    secondary_list = []
    for i in range(5):
         r = room_to_find + i
         if r in valid_rooms:
          secondary_list.append(r)

    #digit = room_to_find// (len(str(room_to_find)))
    #sumer = digit*1000
    #winter = (sumer - room_to_find) + 1
    #fina = winter + room_to_find

    winter = str(room_to_find).ljust(3, "0")
    winter = winter + "1"  
    fina = int(winter)

    for i in range(5):
         f = fina + i
         if f in valid_rooms:
          secondary_list.append(f)

    print(secondary_list)
    return secondary_list



async def configure_priority(level):
    if level == "vip":
        return 4
    elif level == "rep":
        return 3
    elif level == "c":
        return 2
    elif level == "mob":
        return 1
    elif level == "att":
        return 0

async def configure_priority_reverse(level):
   if level == 4:
       return "VIP / Executives"
   elif level == 3:
       return "Repeaters"
   elif level == 2:
       return "C-Report"
   elif level == 1:
       return "Mobility Issues"
   elif level == 0:
       return "Attention"




@sio.event 
async def get_work(sid,data):
    print("[NIGGA]")
    job = data.get("job")
    await work_sender(sid,job)

async def work_sender(sid, job):
    async with app['db_pool'].acquire() as conn:       
        if job == "users":
            rows = await conn.fetch("SELECT name, userid, active FROM users WHERE deleted = false")        
            users_ = [
                {
                    'name': row['name'], 
                    'id': row['userid'], 
                    'status': 'active' if row['active'] else 'inactive'
                } for row in rows
            ]           
            await sio.emit("user_getter", {"users": users_}, to=sid)
            return       
        else:
            rows = await conn.fetch("SELECT name, groomid, active FROM grooms WHERE deleted = false")         
            grooms_ = [
                {
                    'name': row['name'], 
                    'id': row['groomid'], 
                    'status': 'active' if row['active'] else 'inactive'
                } for row in rows
            ]           
            await sio.emit("groom_getter", {"grooms": grooms_}, to=sid)
            return



@sio.event
async def add_user(sid, data):
    allowed_tables = ["users", "grooms"]
    if sid not in connected_admins:
        print(f"[SECURITY] Unauthorized add_user attempt from sid {sid}")
        return

    new_user = data.get("new_user")
    table = data.get("job") 
    name = data.get("name")
    password = data.get("password")
    
    if table not in allowed_tables:
     return

    password_hash = await hash_password(password)

    # Determine the correct ID column name based on the table
    id_column = "groomid" if table == "grooms" else "userid"

    # We use an f-string for the table and column names (identifiers).
    # We use $1, $2, $3 for the data (values).
    query = f"INSERT INTO {table} ({id_column}, name, active,password_hash) VALUES ($1, $2, $3,$4)"

    async with app['db_pool'].acquire() as conn:
        # execute handles the insert and the commit automatically
        await conn.execute(query, new_user, name, True,password_hash)

    print(f"✅ Added {new_user} to {table}")
    await work_sender(sid, table)


sql_activate_users = "UPDATE users SET active = true WHERE userid = $1"
sql_activate_grooms = "UPDATE grooms SET active = true WHERE groomid = $1"
sql_deactivate_users = "UPDATE users SET active = false WHERE userid = $1"
sql_deactivate_grooms = "UPDATE grooms SET active = false WHERE groomid = $1"
sql_delete_users = "UPDATE users SET deleted = true WHERE userid = $1"
sql_delete_grooms = "UPDATE grooms SET deleted = true WHERE groomid = $1"

@sio.event 
async def deactivate_workers(sid, data):

    if sid not in connected_admins:
        print(f"[SECURITY] Unauthorized add_user attempt from sid {sid}")
        return

    print("[DEACTIVATE]")
    table = data.get("table")
    workers = data.get("workers")
    
    query = sql_deactivate_grooms if table == "grooms" else sql_deactivate_users

    async with app['db_pool'].acquire() as conn:
        # We use a transaction so all updates succeed or fail together
        async with conn.transaction():
            for worker in workers:
                worker_id = worker.get("id")
                await conn.execute(query, worker_id)

    await work_sender(sid, table)

@sio.event 
async def activate_workers(sid, data):

    if sid not in connected_admins:
        print(f"[SECURITY] Unauthorized add_user attempt from sid {sid}")
        return

    print("[ACTIVATE]")
    table = data.get("table")
    workers = data.get("workers")
    
    query = sql_activate_grooms if table == "grooms" else sql_activate_users

    async with app['db_pool'].acquire() as conn:
        async with conn.transaction():
            for worker in workers:
                worker_id = worker.get("id")
                await conn.execute(query, worker_id)

    await work_sender(sid, table)

@sio.event 
async def delete_workers(sid, data):

    if sid not in connected_admins:
        print(f"[SECURITY] Unauthorized add_user attempt from sid {sid}")
        return


    print("[DELETE]")
    table = data.get("table")
    workers = data.get("workers")
    
    query = sql_delete_grooms if table == "grooms" else sql_delete_users

    async with app['db_pool'].acquire() as conn:
        async with conn.transaction():
            for worker in workers:
                worker_id = worker.get("id")
                await conn.execute(query, worker_id)

    await work_sender(sid, table)


sql_average_completion_time_for_groom = """
SELECT 
    g.name AS groom_name,
   to_char(AVG(r.finish_time - r.accept_time), 'HH24:MI:SS') AS average_execution_time
FROM requests r
JOIN grooms g ON r.groomid = g.groomid
WHERE r.completed = true
  AND r.finish_time IS NOT NULL
  AND r.accept_time IS NOT NULL
GROUP BY g.groomid, g.name
ORDER BY average_execution_time DESC;
"""

sql_requests_for_every_time_of_day = """
    SELECT 
    to_char(date_trunc('hour', insert_time), 'HH24:00') ||  ' - '  ||
    to_char(date_trunc('hour', insert_time) + interval '1 hour', 'HH24:00') AS time_range,
    COUNT(id) AS total_requests
FROM requests
WHERE insert_time::date = $1
GROUP BY date_trunc('hour', insert_time)
ORDER BY time_range;
"""

sql_average_requests_for_every_time_of_day = """
SELECT 
    to_char(h.hour, 'HH24:00') || ' - ' || to_char(h.hour + interval '1 hour', 'HH24:00') AS time_range,
    COALESCE(COUNT(r.id) / NULLIF(COUNT(DISTINCT date_trunc('day', r.insert_time)), 0), 0) AS total_requests
FROM 
    (SELECT generate_series(
        date_trunc('day', current_date), 
        date_trunc('day', current_date) + interval '23 hours', 
        interval '1 hour'
    ) AS hour) h
LEFT JOIN requests r 
    ON date_part('hour', r.insert_time) = date_part('hour', h.hour)
GROUP BY h.hour
ORDER BY h.hour;
"""


sql_find_daily_late_requests = """
SELECT COUNT(*) AS late_requests
FROM requests
WHERE insert_time::date = $1
  AND finish_time IS NOT NULL
  AND finish_time - insert_time > INTERVAL '15 minutes';

"""



@sio.event 
async def requests_per_day_time(sid):

    now = datetime.now()
    trimmed = datetime(now.year, now.month, now.day)
    #values = (trimmed,)
    #nostoscur.execute(sql_requests_for_every_time_of_day,values)
    #row = nostoscur.fetchall()
    async with app['db_pool'].acquire() as conn:
        row = await conn.fetch(sql_requests_for_every_time_of_day, now)
    print(row)
    hours_json = [
        {"slot": s[0], "count": s[1]}
        for s in row
    ]
    print(hours_json)
    await sio.emit("requests_per_day_time_acceptor",{"hours":hours_json},to=sid)

@sio.event 
async def average_requests_per_day_time(sid):

    #nostoscur.execute(sql_average_requests_for_every_time_of_day)
    #row = nostoscur.fetchall()
    async with app['db_pool'].acquire() as conn:
        row = await conn.fetch(sql_average_completion_time_for_groom)
    print(row)
    average_hours_json = [
        {"slot": s[0], "count": s[1]}
        for s in row
    ]
    print(average_hours_json)
    await sio.emit("average_requests_per_day_time_acceptor",{"hours":average_hours_json},to=sid)

@sio.event
async def average_groom_completion_time(sid):
    #nostoscur.execute(sql_average_completion_time_for_groom)
    #row = nostoscur.fetchall()
    async with app['db_pool'].acquire() as conn:
        row = await conn.fetch(sql_average_completion_time_for_groom)
    print(row)
    grooms_json = [
        {"groomid": u[0], "duration": u[1]}
        for u in row
    ]
    print(grooms_json)
    await sio.emit("average_groom_completion_time_acceptor",{"grooms":grooms_json},to=sid)






        

@sio.event 
async def get_average_requests_per_day(sid):
    global connected_admins_via_userid
    global server_time
    global total_daily_requests
    server_time = datetime.now()
    now = datetime.now()
    #nostoscur.execute(sql_average_requests_for_every_time_of_day)
    #row = nostoscur.fetchall()
    async with app['db_pool'].acquire() as conn:
        row = await conn.fetch(sql_average_requests_for_every_time_of_day)
    print(f"[AVERAGE1]")
    print(row)
    average_hours_json = [
    {"slot": i-1, "count": s[1]}
    for i, s in enumerate(row, start=1)
]
    await sio.emit("average_requests_per_day_time_acceptor",{"hours":average_hours_json},to=sid)
    print(f"[AVERAGE2]: {average_hours_json}")


@sio.emit
async def admin_total_daily_requests_sender_event(sid,data):
     user_id = data.get("user_id")
     global total_daily_requests
     await sio.emit("total_daily_requests_acceptor",{"total_daily_requests":total_daily_requests},to=sid)
            
async def admin_total_daily_requests_sender():
    global total_daily_requests
    global connected_admins_via_userid
    print(f"[TOTAL]: {total_daily_requests}")
    for sid in connected_admins_via_userid.values():
        await sio.emit("total_daily_requests_acceptor",{"total_daily_requests":total_daily_requests},to=sid)
        print(connected_admins_via_userid)
        print(sid)

async def late_requests_for_today_sender():
    now = datetime.now()
    trimmed = datetime(now.year, now.month, now.day)
    #values = (trimmed,)
    #nostoscur.execute(sql_find_daily_late_requests,values)
    #row = nostoscur.fetchone()[0]
    async with app['db_pool'].acquire() as conn:
        row = await conn.fetchval(sql_find_daily_late_requests, now)
    for sid in connected_admins_via_userid.values():
     await sio.emit("late_requests_for_today_acceptor",{"late_requests_for_today":row},to=sid)

@sio.emit 
async def get_late_requests(sid):
    print("[HERE]")
    now = datetime.now()
    trimmed = datetime(now.year, now.month, now.day)
    #values = (trimmed,)
    #nostoscur.execute(sql_find_daily_late_requests,values)
    #row = nostoscur.fetchone()[0]
    async with app['db_pool'].acquire() as conn:
        row = await conn.fetchval(sql_find_daily_late_requests, now)
    print(f"[ROW]: {row}")
    await sio.emit("late_requests_for_today_acceptor",{"late_requests_for_today":row},to=sid)





    
if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=5000)
    