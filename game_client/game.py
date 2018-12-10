import socket
import threading
import pygame
from time import sleep
import json
import copy
import os

p = pygame

p.init()

display = p.display
clock = p.time.Clock()

FPS = 120
frames = FPS / 6

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

try:
    GAME_FONT = pygame.font.Font("8-bit.ttf", 27)
except:
    GAME_FONT = pygame.font.SysFont("Arial", 27)

screen = display.set_mode((800, 800))#, pygame.FULLSCREEN)
display.set_caption("Fortnite MMO RPG Bullet Hell")

w,h = pygame.display.get_surface().get_size()

def text_obj(text, font):
    textSurface = font.render(text, True, WHITE)
    return textSurface, textSurface.get_rect()

def text_to_screen(text, x, y):
    textSurf, textRect = text_obj(text, GAME_FONT)
    textRect.center = ((w/2), (h/2))
    screen.blit(textSurf, textRect)

    display.update()

# - - BORROWED CODE - - https://www.pygame.org/wiki/Spritesheet - -
class SpriteStripAnim(object):
    """sprite strip animator

    This class provides an iterator (iter() and next() methods), and a
    __add__() method for joining strips which comes in handy when a
    strip wraps to the next row.
    """

    def __init__(self, filename, rect, count, colorkey=None, loop=False, frames=1):
        """construct a SpriteStripAnim

        filename, rect, count, and colorkey are the same arguments used
        by spritesheet.load_strip.

        loop is a boolean that, when True, causes the next() method to
        loop. If False, the terminal case raises StopIteration.

        frames is the number of ticks to return the same image before
        the iterator advances to the next image.
        """
        self.filename = filename
        ss = spritesheet(filename)
        self.images = ss.load_strip(rect, count, colorkey)
        self.i = 0
        self.loop = loop
        self.frames = frames
        self.f = frames

    def iter(self):
        self.i = 0
        self.f = self.frames
        return self

    def next(self):
        if self.i >= len(self.images):
            if not self.loop:
                raise StopIteration
            else:
                self.i = 0
        image = self.images[self.i]
        self.f -= 1
        if self.f == 0:
            self.i += 1
            self.f = self.frames
        return image

    def __add__(self, ss):
        self.images.extend(ss.images)
        return self

class spritesheet(object):
    def __init__(self, filename):
        self.sheet = pygame.image.load(filename).convert()
    # Load a specific image from a specific rectangle
    def image_at(self, rectangle, colorkey = None):
        "Loads image from x,y,x+offset,y+offset"
        rect = pygame.Rect(rectangle)
        image = pygame.Surface(rect.size).convert()
        image.blit(self.sheet, (0, 0), rect)
        x,y = image.get_size()
        image = pygame.transform.scale(image, (x*4, y*4))
        if colorkey is not None:
            if colorkey is -1:
                colorkey = image.get_at((0,0))
            image.set_colorkey(colorkey, pygame.RLEACCEL)
        return image
    # Load a whole bunch of images and return them as a list
    def images_at(self, rects, colorkey = None):
        "Loads multiple images, supply a list of coordinates"
        return [self.image_at(rect, colorkey) for rect in rects]
    # Load a whole strip of images
    def load_strip(self, rect, image_count, colorkey = None):
        "Loads a strip of images and returns them as a list"
        tups = [(rect[0]+rect[2]*x, rect[1], rect[2], rect[3]) for x in range(image_count)]
        return self.images_at(tups, colorkey)
# - - END BORROWED CODE - -
class pos():
    def __init__(self, x, y):
        self.x = x
        self.y = y

class packet_handler:
    def handlePacket(self, packet_pass):
        dataDecode = packet_pass.decode()
        packetQueue = dataDecode.split("\n")
        for x in packetQueue:
            if x != "":
                data = json.loads(x)
                packetType = data[0]
                packetData = data[1]
                address = data[2]

                if packetType == "playerJoin":
                    self.playerConnect(packetData, address)
                if packetType == "playerUpdate":
                    print(packetData)
                    self.playerUpdate(packetData, address)
                if packetType == "init":
                    self.init_playerList(packetData)
                if packetType == "playerIdle":
                    self.playerIdle(packetData, address)
                if packetType == "disconnect":
                    self.playerDisconnect(packetData)
                if packetType == "login":
                    self.login(packetData)

    def init_playerList(self, packetData):
        print(packetData)
        for x in packetData:
            packetData[x][1] = pos(packetData[x][1][0], packetData[x][1][1])
            packetData[x] = server_player(packetData[x])
        client.playerList = packetData

    def playerConnect(self, playerData, address):
        playerData[1] = pos(playerData[1][0], playerData[1][1])
        sp = server_player(playerData)
        client.playerList[address] = sp
        player.updatePlayers()
        print(client.playerList)

    def playerDisconnect(self, packetData):
        print(client.playerList)
        del client.playerList[packetData]
        print(client.playerList)

    def playerUpdate(self, playerData, address):
        #try:
        temp = copy.deepcopy(playerData)
        temp[1] = pos(temp[1][0], temp[1][1])
        client.playerList[address].update(temp)
        player.updatePlayers()
        #except:
            #self.playerConnect(playerData, address)

    def playerIdle(self, data, address):
        client.playerList[address].image = client.playerList[address].playerIdle[data]

    def login(self, packetData):
        client.auth = packetData

    def send(self, data):
        toSend = json.dumps(data)+"\n"
        client.sock.send(toSend.encode())

    def player_join(self, playerData):
        self.send(["playerJoin", playerData])

    def player_update(self, playerData):
        self.send(["playerUpdate", playerData])

    def player_idle(self, playerData):
        self.send(["playerIdle", playerData])

    def send_login(self, loginData):
        self.send(["login", loginData])

    def send_register(self, registerData):
        self.send(["register", registerData])

class Client:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    packet = packet_handler()
    playerList = {}

    auth = None

    #def sendMsg(self):
        #while True:
            #self.sock.send(bytes(input(""), 'utf-8'))#https://stackoverflow.com/questions/4342176/how-do-i-serialize-a-python-dictionary-into-a-string-and-then-back-to-a-diction

    def recv(self):
        while True:
            data = self.sock.recv(4096)
            if not data:
                break
            self.packet.handlePacket(data)  # data of packet, who sent it
            #print("recv")

    def __init__(self, address):
        self.sock.connect((address, 10000))

        iThread = threading.Thread(target=self.recv)
        iThread.daemon = True
        iThread.start()

class ground_tile(pygame.sprite.Sprite):
    def __init__(self, path, start_position):
        super().__init__()

        self.image = pygame.image.load(path).convert()
        self.size = self.image.get_size()
        self.image = pygame.transform.scale(self.image, (self.size[0] * 4, self.size[1] * 4))  # scale image
        self.image.set_colorkey(WHITE)

        self.position = pos(start_position[0], start_position[1])

        self.rect = self.image.get_rect()
        self.rect.x = self.position.x
        self.rect.y = self.position.y

    def update(self, playerPos):  # 0 - x, 1 - y
        self.rect.x = self.position.x - playerPos.x
        self.rect.y = self.position.y - playerPos.y

class Player():#player class
    def __init__(self, playerData):#on creation this runs
        #reference all player walking sprites
        #[0] = down, [1] = right, [2] = up, [3] = left
        ss = spritesheet(os.path.abspath('sprites/playerSpriteSheet.png'))#get spritesheet reference
        self.playerIdle = [#list of player idle states
            ss.image_at((0, 8, 8, 8), colorkey=WHITE),#down
            ss.image_at((0, 0, 8, 8), colorkey=WHITE),#right
            ss.image_at((0, 24, 8, 8), colorkey=WHITE),#up
            ss.image_at((0, 16, 8, 8), colorkey=WHITE)#left
        ]
        self.playerWalk = [
            SpriteStripAnim(os.path.abspath('sprites/playerSpriteSheet.png'), (8, 8, 8, 8), 2, WHITE, True, frames),#down
            SpriteStripAnim(os.path.abspath('sprites/playerSpriteSheet.png'), (0, 0, 8, 8), 2, WHITE, True, frames),#right
            SpriteStripAnim(os.path.abspath('sprites/playerSpriteSheet.png'), (8, 24, 8, 8), 2, WHITE, True, frames),#up
            SpriteStripAnim(os.path.abspath('sprites/playerSpriteSheet.png'), (0, 16, 8, 8), 2, WHITE, True, frames)#left
        ]
        self.lastFaced = playerData[0]#last faced
        self.position = playerData[1]
        self.playerAnim = self.playerWalk[self.lastFaced].next()#current animation player is showing
        self.speed = playerData[2]

        self.Idle = True

        self.attacking = False

    def update(self):#called every tick
        self.updatePlayers()
        keys = p.key.get_pressed()#get current keys pressed

        locIdle = True

        #movement
        if keys[p.K_d] and not keys[p.K_a]:#if key d is pressed and not a pressed
            self.position.x += self.speed
            self.playerAnim = player.playerWalk[1].next()#set player animation
            self.lastFaced = 1#set last faced
            tileList.update(self.position)
            client.packet.player_update(self.player_data())
            locIdle = False
        if keys[p.K_a] and not keys[p.K_d]:#if key a is pressed and not d
            self.position.x -= self.speed
            self.playerAnim = player.playerWalk[3].next()#set player animation
            self.lastFaced = 3#set last faced
            tileList.update(self.position)
            client.packet.player_update(self.player_data())
            locIdle = False
        if keys[p.K_w] and not keys[p.K_s]:#if key w is pressed and not s
            self.position.y -= self.speed
            self.playerAnim = player.playerWalk[2].next()#set player animation
            self.lastFaced = 2#set last faced
            tileList.update(self.position)
            client.packet.player_update(self.player_data())
            locIdle = False
        if keys[p.K_s] and not keys[p.K_w]:#if key s is prssed and not w
            self.position.y += self.speed
            self.playerAnim = player.playerWalk[0].next()#set player animation
            self.lastFaced = 0#set last faced
            tileList.update(self.position)
            client.packet.player_update(self.player_data())
            locIdle = False

        if keys[p.K_SPACE]:
            print(client.playerList)

        for event in p.event.get():
            if e.type == p.KEYDOWN:
                if e.key == p.K_x:
                    player.attackToggle()

        if locIdle and self.Idle == False:
            self.Idle = True
            client.packet.player_idle(self.lastFaced)
        else:
            self.Idle = False

        #attacking


        updateScreen()

        

    def attackToggle(self):
        self.attacking = not self.attacking

    def updatePlayers(self):
        for x in client.playerList:
            client.playerList[x].move(self.position)

    def player_data(self):
        return [self.lastFaced, [self.position.x, self.position.y], self.speed]

class server_player():
    def __init__(self, player_data):
        # reference all player walking sprites
        # [0] = down, [1] = right, [2] = up, [3] = left
        ss = spritesheet(os.path.abspath('sprites/playerSpriteSheet.png'))  # get spritesheet reference
        self.playerIdle = [  # list of player idle states
            ss.image_at((0, 8, 8, 8), colorkey=WHITE),  # down
            ss.image_at((0, 0, 8, 8), colorkey=WHITE),  # right
            ss.image_at((0, 24, 8, 8), colorkey=WHITE),  # up
            ss.image_at((0, 16, 8, 8), colorkey=WHITE)  # left
        ]
        self.playerWalk = [
            SpriteStripAnim(os.path.abspath('sprites/playerSpriteSheet.png'), (8, 8, 8, 8), 2, WHITE, True, frames),  # down
            SpriteStripAnim(os.path.abspath('sprites/playerSpriteSheet.png'), (0, 0, 8, 8), 2, WHITE, True, frames),  # right
            SpriteStripAnim(os.path.abspath('sprites/playerSpriteSheet.png'), (8, 24, 8, 8), 2, WHITE, True, frames),  # up
            SpriteStripAnim(os.path.abspath('sprites/playerSpriteSheet.png'), (0, 16, 8, 8), 2, WHITE, True, frames)  # left
        ]
        self.lastFaced = player_data[0]  # last faced
        self.position = player_data[1]
        self.image = self.playerWalk[self.lastFaced].next()  # current animation player is showing
        self.speed = player_data[2]
        self.curPos = copy.deepcopy(self.position)

    def update(self, player_data):
        self.lastFaced = player_data[0]  # last faced
        self.position = player_data[1]
        self.curPos = copy.deepcopy(self.position)
        self.speed = player_data[2]
        self.image = self.playerWalk[self.lastFaced].next()  # current animation player is showing

    def move(self, playerPos):
        self.position.x = self.curPos.x - playerPos.x
        self.position.y = self.curPos.y - playerPos.y
# - - END CLASSES - -

# -- LOG IN --

# -- Once successfully auth'd with server --

#connect to server
while True:
    try:
        client = Client('127.0.0.1')
        break
    except:
        print("unable to conenct to server")

        text_to_screen("Loading Error", 0, 0)

        for e in p.event.get():
            if e.type == p.QUIT:
                p.quit()
                quit()

while True:
    authType = input("login or register: ").lower()
    if authType == "login":
        while True:
            username = input("Username: ")
            password = input("Password: ")
            client.packet.send_login([username, password])
            break
        a = True
        while a:
            if client.auth == True:
                print("successfully logged in, check the game window!")
                a=False
            elif client.auth == False:
                print("auth failed, try again")
                client.auth = None
                break
        else:
            break
    elif authType == "register":
        auth = False
        while not auth:
            username = input("Username: ")
            password = input("Password: ")
            yesOrNo = input("Are you sure you want these credentials (yes/y): ").lower()
            if yesOrNo in ["yes", "y"]:
                client.packet.send_register([username, password])
                auth = True
    else:
        print("that response is invalid")


tileList = pygame.sprite.Group()# create tile list group

run = True

playerStartStats = [0, pos(50, 50), 3]

player = Player(playerStartStats)

client.packet.player_join(player.player_data())

for row in range(0, 64*4, 8*4):#for row in map
    for col in range(0, 64*4, 8*4):#for col in map
        grass = ground_tile('sprites/grass.png', [col+w/2, row+h/2])#create new grass tile

        tileList.add(grass)#add it to the tile list

tileList.update(player.position)

def updateScreen():
    screen.fill(BLACK)#fill the screen
    tileList.draw(screen)

    for x in client.playerList:
        screen.blit(client.playerList[x].image, (client.playerList[x].position.x+w/2, client.playerList[x].position.y+h/2))

    screen.blit(player.playerAnim, (w/2, h/2))#draw player onto the screen
    pygame.display.flip()#update the entire canvas


while run:
    for e in p.event.get():
        if e.type == p.QUIT:
            run = False

    player.update()#run the player update

    clock.tick(FPS)#tick

    player.playerAnim = player.playerIdle[player.lastFaced]# set the anim to idle if nothing was pressed to override it

p.quit()
quit()