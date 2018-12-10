import threading
import socket
import json
import copy
import uuid
#import scrypt

from sqlalchemy import Table, Column, ForeignKey, Integer, MetaData, Text, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# db base declaration
Base = declarative_base()

class User(Base):#user class (for DB)
    __tablename__ = "User"#table name to be put under
    uid = Column(Text, primary_key=True, unique=True)
    username = Column(Text)#defining username column
    password = Column(String)#defining password column
    userdata = Column(Text)#defining a userdata column # a json string

    def __repr__(self):#a return function of helpful information
        return "<User id=%s username=%s stats=%s>" % (self.uid, self.username, self.userdata)

engine = create_engine("sqlite:///database.db")  # create engine (ref to db)
Base.metadata.create_all(engine)  # create all metadata based on ref to db
DBSession = sessionmaker(bind=engine)  # create a session

class player:
    def __init__(self, name, uid, data):
        self.name = name
        self.uid = uid
        self.data = data

class dbInterface():
    def __init__(self):
        self.session = DBSession()  # reference to session

    def newUser(self, username, password, userdata):#function to create a new user for the CLI
        uid = str(uuid.uuid4())
        #password = scrypt.hash(password, uid).hex()
        self.session.add(User(uid=uid, username=username, password=password,userdata=userdata))  # add a new user using the specified arguments
        self.session.commit()  # commit to db

    def auth(self, userdata, connection, address):
        user = self.checkUser(userdata[0])#get ref to user
        if user:#if exists
            if user.password == userdata[1]:  # scrypt.hash(userdata[1], user.uid).hex():#password check
                toSend = json.dumps(["login", True, "server"])#send login packet
                connection.send(toSend.encode())#send the packet

                server.connections[address][2].sendInit(server.players)  # send the initializing packet to new player

                p = player(user.username, user.uid, json.loads(user.userdata))

                server.players[address] = p
                server.connections[address][1] = True#set the auth'd tag to true
            else:
                toSend = json.dumps(["login", False, "server"])#if failed auth send failed packet
                connection.send(toSend.encode())#send packet
        else:
            toSend = json.dumps(["login", False, "server"])  # if failed auth send failed packet
            connection.send(toSend.encode())  # send packet

    def checkUser(self, username):#check if the user exists and return the user
        userRef = self.session.query(User).filter_by(username=username).first()#get reference to user
        if userRef:#if exists
            return userRef#return it
        else:
            print("no users found")
            return None

    def deleteUser(self, username):#delete a user from db
        userRef = self.session.query(User).filter_by(username=username).first()#reference to user
        if userRef:#if exists
            self.session.delete(userRef)#delete user
            self.session.commit()#commit to db
        else:#not found
            print("no user found")
            return None

    def allUsers(self):
        return self.session.query(User).all()  # print all Users in DB

    def saveData(self, uid, data):
        userRef = self.session.query(User).filter_by(uid=uid).first()  # reference to user
        if userRef:
            userRef.userdata = data
            self.session.commit()
        else:
            print("error updating user")

class packet_handler:
    def __init__(self, c, ip, port, address):
        self.connection = c
        self.ip = ip
        self.port  = port
        self.address = address

        self.db = dbInterface()


    def handlePacket(self, packet_pass):#called when packet recieved
        #print(packet_pass.decode())
        dataDecode = packet_pass.decode()#decode the packet
        packetQueue = dataDecode.split("\n")#split the packetqueue
        for x in packetQueue:#for each packet
            if x != "":#if it is not the last in the queue
                data = json.loads(x)#get the packet data
                packetType = data[0]#get the type
                packetData = data[1]#get the data

                if packetType == "playerJoin":#if the packet type is a player join
                    self.player_connect(packetData, data)#run player connect method

                if packetType == "login":#if the packet is a login packet
                    self.login(packetData)#run the login method using the parameters

                if packetType == "register":#if the packet is a register packet
                    self.register(packetData)#run the register method

                if packetType == "playerUpdate":#if it is a player update
                    self.player_update(packetData, data)#run player update method

                if packetType == "playerIdle":#if it is an idle packet
                    self.player_idle(data)#run player idle message

    def sendAll(self, dataREF):
        data = copy.deepcopy(dataREF)  # deep copy the data to avoid overwriting
        data.append(server.players[self.address].name)  # append who sent it
        toSend = json.dumps(data) + "\n"  # packet queue implmentation
        for connection in server.connections:#for each connection
            if server.connections[connection][1] == True and connection != self.address:
                server.connections[connection][0].send(toSend.encode())

    def login(self, userdata):#method to authenticate the user
        self.db.auth(userdata, self.connection, self.address)#run authentication method

    def register(self, userdata):#method to create a new user
        self.db.newUser(userdata[0], userdata[1], json.dumps([0, [50, 50], 3]))#run method from db interface to create a new user

    def player_connect(self, playerData, packet_pass):#on player connect
        self.sendAll(["playerJoin", server.players[self.address].data])#send a packet to all other players (same packet recieved)
        server.players[self.address].data = playerData#add to player dictionary

    def player_update(self, playerData, packet_pass):#on player update
        self.sendAll(packet_pass)#send the packet to everyone
        server.players[self.address].data = playerData#update the dictionary of players

    def player_idle(self, packet_pass):#if player idle
        self.sendAll(packet_pass)#send to all other players (really just to stop the anim)

    def sendInit(self, dataREF):#method to send online player dictionary to new players
        data = copy.deepcopy(dataREF)#deep copy to avoid overwrites
        sendable = {}
        for x in data:
            ref = data[x]
            sendable[ref.name] = ref.data
        toSend = json.dumps(["init", sendable, "server"])#dump it to json to send
        self.connection.send(toSend.encode())#send

class commandHandler:#command handler class
    db = dbInterface()#ref to the database interface

    def __init__(self):#on init
        commandThread = threading.Thread(target=self.commands)#create the command thread
        commandThread.daemon = True#daemon
        commandThread.start()#start thread

    def commands(self):#running in the command thread
        while True:#loop
            temp = input()
            temp = temp.split()
            if len(temp) > 0:#check if there is anything there
                temp = [_.lower() for _ in temp]#lowercase all arguments
                cmd = temp[0]#get command header
                args = []#create an empty args array
                if len(temp) > 1:#if there are any arguments
                    args = temp[1:]#set args equal to them

                if cmd == "list":#if the command is list
                    print(server.players)#list all players
                    print(server.connections)
                elif cmd in ["stop", "sotp"]:#if the command is to stop
                    print("Stopping Server")#stop the server IO
                    quit()
                elif cmd == "user" and len(args) is not 0:#if the command is user
                    if args[0] in ["create", "new"]:#create argument?
                        if len(args) == 4:
                            self.db.newUser(args[1], args[2], args[3])#create a new user using inputted parameters
                        else:
                            print("usage: user <new/create> <username> <password> <userdata>")
                    elif args[0] == "all":#if qrgument is all
                        print(self.db.allUsers())
                    elif args[0] in ["delete", "remove"]:#if arguemnt is to delete and there is a second argument
                        if len(args) == 2:#if enough arguments
                            self.db.deleteUser(args[1])#delete a user of username inputed
                        else:
                            print("usage: user <delete, remove> <username>")
                elif len(args) == 0 and cmd == "user":
                    print("Usage: user <create, new, all, delete, remove>")

class server:
    threads = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)#reference to used socket
    connections = {}
    players = {}

    def __init__(self):
        self.cmd = commandHandler()
        self.sock.bind(('0.0.0.0', 10000))  # bind to socket
        self.sock.listen(1)  # begin listening on the socket

    def closeConnection(self, c, a, p):
        print("BEGIN DISCONNECT")
        print(self.connections)
        print(self.players)
        print(a)
        print(str(a[0]) + ":" + str(a[1]) + " disconnected")  # print to console of server who disconnected
        toSend = json.dumps(["disconnect", self.players[str(a[0]) + ":" + str(a[1])].name, "server"])#prepare packet
        p.db.saveData(self.players[str(a[0]) + ":" + str(a[1])].uid, json.dumps(self.players[str(a[0]) + ":" + str(a[1])].data))
        del self.connections[str(a[0]) + ":" + str(a[1])]
        c.close()  # close the connection
        del self.players[str(a[0]) + ":" + str(a[1])]  # remove the user from the players dictionary

        for c in self.connections:
            self.connections[c][0].send(toSend.encode())

        print(self.connections)
        print(self.players)
        print("END DISCONNECT")

    def handler(self, c, a, userData):
        packet = userData[2]
        connected = True
        while connected:
            try:  # try this
                data = c.recv(1024)  # recieve a set amount of data
                packet.handlePacket(data)  # send it to be parsed
            except:  # if a disconnect from socket (errors out lol)
                self.closeConnection(c, a, packet, connected)
                break

    def run(self):  # main server loop
        while True:  # main server loop
            c, a = self.sock.accept()  # accept any new connections

            p = packet_handler(c, str(a[0]), str(a[1]), str(a[0]) + ":" + str(a[1]))
            #add to connections
            self.connections[str(a[0]) + ":" + str(a[1])] = [c, False, p]

            # begin listening for player packets
            lThread = threading.Thread(target=self.handler, args=(c, a, self.connections[str(a[0]) + ":" + str(a[1])]))  # begin listening on the socket for them and any packets they send
            lThread.start()  # start thread
            self.threads[str(a[0]) + ":" + str(a[1])] = lThread

            print(str(a[0]) + ':' + str(a[1]), "connected")  # print to console user connected

server = server()
server.run()