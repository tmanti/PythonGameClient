import threading
import socket
import json
import copy

class pos():
    def __init__(self, x, y):
        self.x = x
        self.y = y

class packet_handler:
    def handlePacket(self, packet_pass, ip, port):
        #print(packet_pass.decode())
        dataDecode = packet_pass.decode()
        packetQueue = dataDecode.split("\n")
        for x in packetQueue:
            if x != "":
                data = json.loads(x)
                packetType = data[0]
                packetData = data[1]

                if packetType == "playerJoin":
                    self.player_connect(ip, port, packetData, data)

                if packetType == "playerUpdate":
                    self.player_update(ip, port, packetData, data)

                if packetType == "playerIdle":
                    self.player_idle(ip, port, data)

    def player_connect(self, ip, port, playerData, packet_pass):
        self.sendPacket(ip, port, packet_pass)
        playerData[1] = pos(playerData[1][0], playerData[1][1])
        server.players[str(ip) + ':' + str(port)] = playerData
        print(server.players)

    def player_update(self, ip, port, playerData, packet_pass):
        self.sendPacket(ip, port, packet_pass)
        playerData[1] = pos(playerData[1][0], playerData[1][1])
        server.players[str(ip) + ':' + str(port)] = playerData
        #print(ip + " " + str(server.players[ip][1].x) + ", " + str(server.players[ip][1].y))

    def player_idle(self, ip, port, packet_pass):
        self.sendPacket(ip, port, packet_pass)

    def sendPacket(self, ip, port, dataREF):
        data = copy.deepcopy(dataREF)
        for connection in server.connections:
            if not(str(connection[1][0]) == ip and str(connection[1][1]) == port):
                data.append(str(ip) + ':' + str(port))
                toSend = json.dumps(data) + "\n"
                connection[0].send(toSend.encode())

    def sendInit(self, connection, dataREF):
        data = copy.deepcopy(dataREF)
        for x in data:
            data[x][1] = [data[x][1].x, data[x][1].y]
        toSend = json.dumps(["init", data, "server"])
        connection.send(toSend.encode())

    def sendDisconnect(self, dataREF):
        data = copy.deepcopy(dataREF)
        for x in data:
            data[x][1] = [data[x][1].x, data[x][1].y]
        toSend = json.dumps(["disconnect", data, "server"])

        for connection in server.connections:
            connection[0].send(toSend.encode())

class Player():
    def __init__(self, player_data):
        self.lastFaced = player_data[0]  # last faced
        self.position = player_data[1]
        self.playerAnim = self.playerWalk[self.lastFaced].next()  # current animation player is showing
        self.speed = player_data[2]


class Server:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connections = []
    players = {}
    packet = packet_handler()

    def __init__(self):
        self.sock.bind(('0.0.0.0', 10000))
        self.sock.listen(1)


    def handler(self, c, a):
        while True:
            try:
                data = c.recv(1024)
                self.packet.handlePacket(data, str(a[0]), str(a[1]))#data of packet, who sent it
            except:
                print(str(a[0]) + ':' + str(a[1]), "disconnected")
                self.connections.remove([c, a])
                c.close()
                del self.players[str(a[0]) + ":" +  str(a[1])]
                self.packet.sendDisconnect(self.players)
                break

    def run(self):
        cmd = commandHandler(server)
        while True:
            c, a = self.sock.accept()

            #begin listening for player packets
            lThread = threading.Thread(target=self.handler, args=(c, a))
            lThread.daemon = True
            lThread.start()

            self.connections.append([c, a])
            print(str(a[0]) + ':' + str(a[1]), "connected")
            self.packet.sendInit(c, server.players)

class commandHandler:
    def __init__(self, ref):
        commandThread = threading.Thread(target=self.commands)
        commandThread.daemon = True
        commandThread.start()

    def commands(self):
        while True:
            cmd = input()
            if cmd == "list":
                print(server.players)


server = Server()
server.run()