import threading
import socket
import json
import copy

class pos():#position data type
    def __init__(self, x, y):
        self.x = x
        self.y = y

class packet_handler:#packet handler
    def handlePacket(self, packet_pass, ip, port):#called when packet recieved
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

                if packetType == "playerUpdate":#if it is a player update
                    self.player_update(ip, port, packetData, data)#run player update method

                if packetType == "playerIdle":#if it is an idle packet
                    self.player_idle(ip, port, data)#run player idle message

    def player_connect(self, ip, port, playerData, packet_pass):#on player connect
        self.sendPacket(ip, port, packet_pass)#send a packet to all other players (same packet recieved)
        playerData[1] = pos(playerData[1][0], playerData[1][1])#format position as position data type
        server.players[str(ip) + ':' + str(port)] = playerData#add to player dictionary

    def player_update(self, ip, port, playerData, packet_pass):#on player update
        self.sendPacket(ip, port, packet_pass)#send the packet to everyone
        playerData[1] = pos(playerData[1][0], playerData[1][1])#format position as position data type
        server.players[str(ip) + ':' + str(port)] = playerData#update the dictionary of players
        #print(ip + " " + str(server.players[ip][1].x) + ", " + str(server.players[ip][1].y))

    def player_idle(self, ip, port, packet_pass):#if player idle
        self.sendPacket(ip, port, packet_pass)#send to all other players (really just to stop the anim)

    def sendPacket(self, ip, port, dataREF):#a method to send a packet to everyone connected
        data = copy.deepcopy(dataREF)#deep copy the data to avoid overwriting
        for connection in server.connections:#for each connection
            if not(str(connection[1][0]) == ip and str(connection[1][1]) == port):#if it is not the sender of the packet
                data.append(str(ip) + ':' + str(port))#append who sent it
                toSend = json.dumps(data) + "\n"#packet queue implmentation
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


class Server:#main server class
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)#reference to used socket
    connections = []#connections array
    players = {}#connected players dictionary
    packet = packet_handler()#reference to packet handler

    def __init__(self):#on server initialization
        self.sock.bind(('0.0.0.0', 10000))#bind to socket
        self.sock.listen(1)#begin listening on the socket


    def handler(self, c, a):#packet handler (normally a thread)
        while True:#forever loop
            try:#try this
                data = c.recv(1024)#recieve a set amount of data
                self.packet.handlePacket(data, str(a[0]), str(a[1]))#send it to be parsed
            except:#if a disconnect from socket (errors out lol)
                print(str(a[0]) + ':' + str(a[1]), "disconnected")#print to console of server who disconnected
                self.connections.remove([c, a])#remove it from connections list
                c.close()#close the connection
                del self.players[str(a[0]) + ":" +  str(a[1])] #remove the user from the players dictionary
                self.packet.sendDisconnect(str(a[0]) + ":" +  str(a[1]))#send a packet to the remaining players
                break#stop the loop and then resulting in the stopping of the thread

    def run(self):#main server loop
        cmd = commandHandler(server)#begin the command handler thread
        while True:# main server loop
            c, a = self.sock.accept()#accept any new connections

            #begin listening for player packets
            lThread = threading.Thread(target=self.handler, args=(c, a))#begin listening on the socket for them and any packets they send
            lThread.daemon = True#daemon thread
            lThread.start()#start thread

            self.connections.append([c, a])#append the connection and ip data to the connections list
            print(str(a[0]) + ':' + str(a[1]), "connected")#print to console user connected
            self.packet.sendInit(c, server.players)#send the initializing packet to new player

class commandHandler:#command handler class
    def __init__(self, ref):#on init
        commandThread = threading.Thread(target=self.commands)#create the command thread
        commandThread.daemon = True#daemon
        commandThread.start()#start thread

    def commands(self):#running in the command thread
        while True:#loop
            cmd = input()#
            if cmd == "list":
                print(server.players)
            if cmd == "stop" or cmd == "sotp":
                print("Stopping Server")
                exit()

server = Server()
server.run()