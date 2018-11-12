
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

class dbInterface():
    def __init__(self):
        self.session = DBSession()  # reference to session

    def newUser(self, username, password, userdata):#function to create a new user for the CLI
        uid = str(uuid.uuid4())
        #password = scrypt.hash(password, uid).hex()
        self.session.add(User(uid=uid, username=username, password=password,userdata=userdata))  # add a new user using the specified arguments
        self.session.commit()  # commit to db

    def auth(self, userdata, connection, ip, port):
        user = self.checkUser(userdata[0])#get ref to user
        if user:#if exists
            if user.password == userdata[1]:  # scrypt.hash(userdata[1], user.uid).hex():#password check
                toSend = json.dumps(["login", True, "server"])#send login packet
                connection.send(toSend.encode())#send the packet

                server.packet.sendInit(connection, server.players)  # send the initializing packet to new player

                server.cus.add(str(ip) + ":" + str(port), user.username)#add user data to dicts
            else:
                toSend = json.dumps(["login", False, "server"])#if failed auth send failed packet
                connection.send(toSend.encode())#send packet

    def checkUser(self, username):#check if the user exists and return the user
        print("Checking user")
        print(self.session)
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

class pos():#position data type
    def __init__(self, x, y):
        self.x = x
        self.y = y

class connectedUserStorage():
    playerUsername = {} #username to ip
    playerIp = {} #ip to username

    def add(self, ip, username):#add new user to dictionaries
        self.playerUsername[username] = ip#add the username to ip
        self.playerIp[ip] = username#add the ip to username

    def remove(self, ip):#remove from dictionaries
        del self.playerUsername[self.playerIp[ip]]#remove username
        del self.playerIp[ip]#remove ip

class packet_handler:#packet handler
    def __init__(self):
        self.db = dbInterface()  # ref to the database interface

    def handlePacket(self, packet_pass, ip, port, connection):#called when packet recieved
        #print(packet_pass.decode())
        dataDecode = packet_pass.decode()#decode the packet
        packetQueue = dataDecode.split("\n")#split the packetqueue
        for x in packetQueue:#for each packet
            if x != "":#if it is not the last in the queue
                data = json.loads(x)#get the packet data
                packetType = data[0]#get the type
                packetData = data[1]#get the data

                if packetType == "playerJoin":#if the packet type is a player join
                    self.player_connect(ip, port, packetData, data)#run player connect method

                if packetType == "login":#if the packet is a login packet
                    self.login(ip, port, packetData, connection)#run the login method using the parameters

                if packetType == "register":#if the packet is a register packet
                    self.register(ip, port, packetData)#run the register method

                if packetType == "playerUpdate":#if it is a player update
                    self.player_update(ip, port, packetData, data)#run player update method

                if packetType == "playerIdle":#if it is an idle packet
                    self.player_idle(ip, port, data)#run player idle message

    def player_connect(self, ip, port, playerData, packet_pass):#on player connect
        self.sendPacket(ip, port, packet_pass)#send a packet to all other players (same packet recieved)
        playerData[1] = pos(playerData[1][0], playerData[1][1])#format position as position data type
        server.players[server.cus.playerIp[str(ip) + ':' + str(port)]] = playerData#add to player dictionary

    def player_update(self, ip, port, playerData, packet_pass):#on player update
        self.sendPacket(ip, port, packet_pass)#send the packet to everyone
        playerData[1] = pos(playerData[1][0], playerData[1][1])#format position as position data type
        server.players[server.cus.playerIp[str(ip) + ':' + str(port)]] = playerData#update the dictionary of players
        #print(ip + " " + str(server.players[ip][1].x) + ", " + str(server.players[ip][1].y))

    def player_idle(self, ip, port, packet_pass):#if player idle
        self.sendPacket(ip, port, packet_pass)#send to all other players (really just to stop the anim)

    def login(self, ip, port, userdata, connection):#method to authenticate the user
        self.db.auth(userdata, connection, ip, port)#run authentication method

    def register(self, ip, port, userdata):#method to create a new user
        self.db.newUser(userdata[0], userdata[1], "")#run method from db interface to create a new user

    def sendPacket(self, ip, port, dataREF):#a method to send a packet to everyone connected
        data = copy.deepcopy(dataREF)#deep copy the data to avoid overwriting
        data.append(server.cus.playerIp[str(ip) + ':' + str(port)])  # append who sent it
        toSend = json.dumps(data) + "\n"  # packet queue implmentation
        for connection in server.connections:#for each connectionz
            if not(str(connection[1][0]) == ip and str(connection[1][1]) == port):#if it is not the sender of the packet
                connection[0].send(toSend.encode())#send the packet

    def sendInit(self, connection, dataREF):#method to send online player dictionary to new players
        data = copy.deepcopy(dataREF)#deep copy to avoid overwrites
        for x in data:#for each data
            data[x][1] = [data[x][1].x, data[x][1].y]#set to an array so it can be parsed by json
        toSend = json.dumps(["init", data, "server"])#dump it to json to send
        connection.send(toSend.encode())#send

    def sendDisconnect(self, data):#method to send disconnect packet
        toSend = json.dumps(["disconnect", data, "server"])#prepare packet

        for connection in server.connections:#for each connection
            connection[0].send(toSend.encode())#send the packet

class Player():#player object
    def __init__(self, player_data):#on creation
        self.lastFaced = player_data[0]  # last faced
        self.position = player_data[1]#position
        self.playerAnim = self.playerWalk[self.lastFaced].next()  # current animation player is showing
        self.speed = player_data[2]#speed of player

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
                    print(server.cus.playerIp)
                    print(server.cus.playerUsername)
                elif cmd in ["stop", "sotp"]:#if the command is to stop
                    print("Stopping Server")#stop the server IO
                    exit()
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

class Server:#main server class
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)#reference to used socket
    connections = []#connections array
    cus = connectedUserStorage()
    players = {}#connected players dictionary
    packet = packet_handler()#reference to packet handler

    def __init__(self):#on server initialization
        self.cmd = commandHandler()  # begin the command handler thread
        self.sock.bind(('0.0.0.0', 10000))#bind to socket
        self.sock.listen(1)#begin listening on the socket

    def closeConnection(self, c, a, p):
        print(self.cus.playerIp[str(a[0]) + ':' + a[1]] + "disconnected")  # print to console of server who disconnected
        self.connections.remove([c, a, p])  # remove it from connections list
        c.close()  # close the connection
        del self.players[self.cus.playerIp[str(a[0]) + ':' + a[1]]]  # remove the user from the players dictionary
        self.cus.remove(str(a[0]) + ':' + a[1])
        p.sendDisconnect(str(a[0]) + ":" + str(a[1]))  # send a packet to the remaining players

    def handler(self, c, a, p):#packet handler (normally a thread)
        while True:#forever loop
            try:#try this
                data = c.recv(1024)#recieve a set amount of data
                p.handlePacket(data, str(a[0]), str(a[1]), c)#send it to be parsed
            except:#if a disconnect from socket (errors out lol)
                self.closeConnection(c, a, p)

    def run(self):#main server loop
        while True:# main server loop
            c, a = self.sock.accept()#accept any new connections

            p = packet_handler()
            server.connections.append([c, a, p])  # append the connection and ip data to the connections list

            #begin listening for player packets
            lThread = threading.Thread(target=self.handler, args=(c, a, p))#begin listening on the socket for them and any packets they send
            lThread.daemon = True#daemon thread
            lThread.start()#start thread

            print(str(a[0]) + ':' + str(a[1]), "connected")#print to console user connected

# Below adds to database
# Dont do multiple times, multiple users cannot have the same ids
#session.add(User(id = 4, name = "Bob"))
#session.add(User(id = 5, name = "George"))
#session.query(User).filter_by(username=name).first()

server = Server()
server.run()

# Server class
# Must contain members
# - connections: a map of <ip>:<port> to their connection, their packet handler.
#   It should also contain whether they are authenticated.
#   If they are authenticated, store their uid, to uniquely identify them, allowing you to query them at any time.
#
#