#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

"""
Abraham Hindle's code for websocket.

in his code, the architechture for this:
for each incoming msg from index.html(aka when user draw something there):
    for each clients
        add msg to a client's queue
definitions:
    client: just a queue, each client uses its own websocket to communicate with server
    greenlet: 
        -light weight thread create and managed by gevent library.o
        -can only run on one cpu so there is no real parallelism, only context switches
        -no race condition because of no real parallelism
        -good for I/O bounding tasks
        async operations with gevent, but not parallel as these operations run on the same thread`

#https://github.com/abramhindle/WebSocketsExamples/blob/master/broadcaster.py
#https://github.com/abramhindle/WebSocketsExamples/blob/master/chat.py
"""

class Client:
    """
    from          
    https://github.com/abramhindle/WebSocketsExamples/blob/master/chat.py
    
    client is just a queue
    """
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, v):   # put to the queue withouth blocking 
        self.queue.put_nowait(v)

    def get(self):
        return self.queue.get()

clients = list()   # lists of webclient that wants to communcate with this server


def set_listener( entity, data ):

    ''' do something with the update ! '''
    

    """
    this function is like a callback, add something to the queue somewhere everytime the world notify all listeners, this function will be called

    each websocket should have a queue of msges. 

    everytime the index.html send msg to socket here, the world call notifylistener and we enqueue the msg to all the client's msg queue

    parameters:
         -entity: int that represent entity id
         -data: {x: int, y:int, color: str, radius: int}  the info about entity

    """
    entityCoord = {
        entity: data
    }
    #print("in set_listener, entity is ", entity, " data is ", data)
    for client in clients:
        #print("data is ", {entity: data})
        client.put(json.dumps(entityCoord))  #  enequeu this entity to this client's queue to be read later in subscrib_ function






myWorld = World()        
myWorld.add_set_listener( set_listener )

        
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return flask.redirect("static/index.html") 

def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world
    
    
    # this implementation is from https://github.com/abramhindle/WebSocketsExamples/blob/master/chat.py
    
    '''

    # XXX: TODO IMPLEMENT ME
    
    while True:
        # every packet we received from the index.html
        msg = ws.receive()
        #print ("WS RECV: %s" % msg)
        if (msg is not None):
            packet = json.loads(msg)
            header = ""
            for k1, v1 in packet.items():
                header = k1
            if (v1 == "HELLO"):
                print("received handshake 1 data ", packet)
            else:
                # add this to the msg queue of clients. 
                # packet = {entityid:  {x: int, y:int, color: str, radius: int}}
                for entityid, body in packet.items():  # one iteration loop
                    #print("entity id is ", entityid, "entity body is ", body)
                    myWorld.set(entityid, body)  # this will call update on all client's listener to update client state(enqueue this entity body)
        else:
           break 

         
    

@sockets.route('/subscribe')  # end point for a client to subscribe to a websocket
def subscribe_socket(ws):
    '''
    
    # this implementation is from https://github.com/abramhindle/WebSocketsExamples/blob/master/chat.py


    Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket . each subscribe_socket() greenlet is responsible for one client
       
       #NOTE, can  subscribe_socket() be run on parallel? like if multiple request to this endpoint happens
        ws - wweb socket file descriptor
       
       1. create a client(Queue)
       2. add this client to the list of clients
       3. spawn a greenlet thread     g = gevnet.spawn(   read_ws, ws , client) to make thread of  read_ws  with parameter (ws, client) concurrently
           - gevent.spawn() is like pthrea_create()     needs to be joined 
       
       resource of gevenet:
          https://sdiehl.github.io/gevent-tutorial/ 
    '''
    # XXX: TODO IMPLEMENT ME
    client = Client()
    clients.append(client)
    # we want to  fire up this thread. do we need to join threads?
    # NO, because we want to run the loop on line 192 after this thread runs in the background 
    thread_ = gevent.spawn(read_ws, ws, client)   
    

    #  keep trying to pop data from this client
    try:
        while True:
            #print("before client.get")
            msg = client.get()  # pop the top of the msg stack and send it over to this websocket to the webclient
            #print("msg popped from client queue is ", msg)
            ws.send(msg)   # send back the data to the index.html to update the state there
    except Exception as e:  # WebSocketError as e:
        print("WS Error %s" % e)
    finally:
        print("wesocket killed")
        clients.remove(client)
        gevent.kill(thread_)



# I give this to you, this is how you get the raw body/data portion of a post in flask
# this should come with flask but whatever, it's not my project.
def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data.decode("utf8") != u''):
        return json.loads(request.data.decode("utf8"))
    else:
        return json.loads(request.form.keys()[0])

"""
there endpoint below are from my ajax assignment

"""


@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    # entity is the entityID, an INT
    # so we wanna populate {entityID : {'x': 1, 'y': 2}}
    postResponseBody = flask_post_json()  # get the response body of post /entity/<eneity> this is {'', ''} type
    # entity is a json object of a dictionary

    if request.method == 'POST':
        myWorld.set(entity, postResponseBody)
        entityGET = myWorld.get(entity)  # get by the enitty ID, this returns the value of entity 
        # so if entity = {entity: {body}}, this returns the body
        return entityGET
    # PUT METHOD, so  will update ----------------------------------------------
    for k, v in postResponseBody.items():  # 1 iteration loop
        myWorld.update(entity, k, v)
    entityGET = myWorld.get(entity)  # get by the enitty ID, this returns the value of entity 
    # so if entity = {entity: {body}}, this returns the body
    return entityGET

@app.route("/world", methods=['POST','GET'])    
def world():
    '''you should probably return the world here'''
    return myWorld.world()

@app.route("/entity/<entity>")    
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    print("type of entity is ", type(entity))
    # flask now will automatically cann jsonify so we can return python dict directly
    return myWorld.get(entity)


@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    myWorld.clear()
    return myWorld.world()



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
