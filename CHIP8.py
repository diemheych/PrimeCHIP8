#PYTHON name
#
#    CHIP8.py - see https://github.com/diemheych/PrimeCHIP8
#
import sys
import uio
import hpprime
import graphic
import urandom

class Register:
    def __init__(self, bits):
        self.value = 0
        self.bits = bits
    
    '''
    def checkFlag(self):
        hexValue = hex(self.value)[2:]
        carryORborrow = False

        if self.value < 0:
            self.value = abs(self.value)
            carryORborrow = True

        if len(hexValue) > self.bits / 4:
            self.value = int(hexValue[-int(self.bits / 4):], 16)
            carryORborrow = True

        if carryORborrow:
            return 1
        return 0
    '''

    def checkCarry(self):
        hexValue = hex(self.value)[2:]

        if len(hexValue) > self.bits / 4:
            self.value = int(hexValue[-int(self.bits / 4):], 16)
            return 1
        
        return 0
    
    def checkBorrow(self):
        if self.value < 0:
            self.value = abs(self.value)
            return 0
        
        return 1
    
    def readValue(self):
        return hex(self.value)
    
    def setValue(self, value):
        self.value = value

class DelayTimer:
    def __init__(self):
        self.timer = 0
    
    def countDown(self):
        if self.timer > 0:
            self.timer -= 1

    def setTimer(self, value):
        self.timer = value
    
    def readTimer(self):
        return self.timer

class SoundTimer(DelayTimer):
    def __init__(self):
        DelayTimer.__init__(self)

    def beep(self):
        if self.timer > 1:
#            os.system('play --no-show-progress --null --channels 1 synth %s triangle %f' % (self.timer / 60, 440))
            self.timer = 0

class Stack:
    def __init__(self):
        self.stack = []
    
    def push(self, value):
        self.stack.append(value)
    
    def pop(self):
        return self.stack.pop()

class Emulator:
    def __init__(self):
        if hpprime.eval("version(2)") == "Emu":
            self.delay = 15
            self.emu = 1
        else:
            self.delay = 2
            self.emu = 0

        self.ticks = 0
        self.dirty = 0
        self.Memory = bytearray(4096)

        fonts = [ 
        0xF0, 0x90, 0x90, 0x90, 0xF0, # 0
        0x20, 0x60, 0x20, 0x20, 0x70, # 1
        0xF0, 0x10, 0xF0, 0x80, 0xF0, # 2
        0xF0, 0x10, 0xF0, 0x10, 0xF0, # 3
        0x90, 0x90, 0xF0, 0x10, 0x10, # 4
        0xF0, 0x80, 0xF0, 0x10, 0xF0, # 5
        0xF0, 0x80, 0xF0, 0x90, 0xF0, # 6
        0xF0, 0x10, 0x20, 0x40, 0x40, # 7
        0xF0, 0x90, 0xF0, 0x90, 0xF0, # 8
        0xF0, 0x90, 0xF0, 0x10, 0xF0, # 9
        0xF0, 0x90, 0xF0, 0x90, 0x90, # A
        0xE0, 0x90, 0xE0, 0x90, 0xE0, # B
        0xF0, 0x80, 0x80, 0x80, 0xF0, # C
        0xE0, 0x90, 0x90, 0x90, 0xE0, # D
        0xF0, 0x80, 0xF0, 0x80, 0xF0, # E
        0xF0, 0x80, 0xF0, 0x80, 0x80  # F
        ]
        for i in range(len(fonts)):
            self.Memory[i] = fonts[i]

        self.Registers = []
        for i in range(16):
            self.Registers.append(Register(8))
        
        self.IRegister = Register(16)
        self.ProgramCounter = 512

        self.stack = Stack()

        self.delayTimer = DelayTimer()
        self.soundTimer = SoundTimer()
        
        self.keys = []
        for i in range(0, 16):
            self.keys.append(False)
        self.keyDict = {
            32 : 1,
            33 : 2,
            34 : 3,
            35 : 0xc,
            37 : 4,
            38 : 5,
            39 : 6,
            40 : 0xd,
            42 : 7,
            43 : 8,
            44 : 9,
            45 : 0xe,
            47 : 0xa,
            48 : 0,
            49 : 0xb,
            50 : 0xf
        }

        self.grid = []
        for i in range(32):
            line = []
            for j in range(64):
                line.append(0)
            self.grid.append(line)
        self.emptyGrid = self.grid[:]
        self.zeroColor = 0xffffff # white
        self.oneColor = 0x0000ff  # blue

        self.size = 10
        width = 64
        height = 32
    
    def execOpcode(self, opcode):
        #print(opcode)

        if opcode[0] == '0':

            if opcode[1] != '0':
                #0NNN

                print("ROM attempts to run RCA 1802 program at <0x" + opcode[1:] + '>')

            else:
                if opcode == '00e0':
                    #00E0
                    #disp_clear()
                    
                    self.clear()

                elif opcode == '00ee':
                    #00EE
                    #return;

                    self.ProgramCounter = self.stack.pop()
        
        elif opcode[0] == '1':
            #1NNN
            #goto NNN;

            self.ProgramCounter = int(opcode[1:], 16) - 2
        
        elif opcode[0] == '2':
            #2NNN
            #*(0xNNN)()

            self.stack.push(self.ProgramCounter)
            self.ProgramCounter = int(opcode[1:], 16) - 2
        
        elif opcode[0] == '3':
            #3XNN
            #if(Vx==NN)

            vNum = int(opcode[1], 16)
            targetNum = int(opcode[2:], 16)

            if self.Registers[vNum].value == targetNum:
                self.ProgramCounter += 2

        elif opcode[0] == '4':
            #4XNN
            #if(Vx!=NN)

            vNum = int(opcode[1], 16)
            targetNum = int(opcode[2:], 16)

            if self.Registers[vNum].value != targetNum:
                self.ProgramCounter += 2

        elif opcode[0] == '5':
            #5XY0
            #if(Vx==Vy)

            v1 = int(opcode[1], 16)
            v2 = int(opcode[2], 16)

            if self.Registers[v1].value == self.Registers[v2].value:
                self.ProgramCounter += 2

        elif opcode[0] == '6':
            #6XNN
            #Vx = NN

            vNum = int(opcode[1], 16)
            targetNum = int(opcode[2:], 16)

            self.Registers[vNum].value = targetNum
        
        elif opcode[0] == '7':
            #7XNN
            #Vx += NN

            vNum = int(opcode[1], 16)
            targetNum = int(opcode[2:], 16)


            self.Registers[vNum].value = (self.Registers[vNum].value + targetNum) & 255
#            self.Registers[vNum].checkCarry()
        
        elif opcode[0] == '8':
            if opcode[3] == '0':
                #8XY0
                #Vx=Vy

                v1 = int(opcode[1], 16)
                v2 = int(opcode[2], 16)

                self.Registers[v1].value = self.Registers[v2].value
            
            elif opcode[3] == '1':
                #8XY1
                #Vx=Vx|Vy

                v1 = int(opcode[1], 16)
                v2 = int(opcode[2], 16)

                self.Registers[v1].value = self.Registers[v1].value | self.Registers[v2].value
            
            elif opcode[3] == '2':
                #8XY2
                #Vx=Vx&Vy

                v1 = int(opcode[1], 16)
                v2 = int(opcode[2], 16)

                self.Registers[v1].value = self.Registers[v1].value & self.Registers[v2].value
            
            elif opcode[3] == '3':
                #8XY3
                #Vx=Vx^Vy

                v1 = int(opcode[1], 16)
                v2 = int(opcode[2], 16)

                self.Registers[v1].value = self.Registers[v1].value ^ self.Registers[v2].value
            
            elif opcode[3] == '4':
                #8XY4
                #Vx += Vy

                v1 = int(opcode[1], 16)
                v2 = int(opcode[2], 16)

                if (self.Registers[v1].value + self.Registers[v2].value) > 255:
                    self.Registers[0xf].value = 1
                else:
                    self.Registers[0xf].value = 0

                self.Registers[v1].value = (self.Registers[v1].value + self.Registers[v2].value) & 255
            
            elif opcode[3] == '5':
                #8XY5
                #Vx -= Vy

                v1 = int(opcode[1], 16)
                v2 = int(opcode[2], 16)

                if self.Registers[v1].value > self.Registers[v2].value:
                    self.Registers[0xf].value = 1
                else:
                    self.Registers[0xf].value = 0

#                self.Registers[v1].value -= self.Registers[v2].value
                self.Registers[v1].value = (self.Registers[v1].value - self.Registers[v2].value) & 255
           
            elif opcode[3] == '6':
                #8XY6
                #Vx>>1

                v1 = int(opcode[1], 16)
#                leastBit = int(bin(self.Registers[v1].value)[-1])
                leastBit = self.Registers[v1].value & 1

                self.Registers[v1].value = self.Registers[v1].value >> 1
                self.Registers[0xf].value = leastBit
            
            elif opcode[3] == '7':
                #8XY7
                #Vx=Vy-Vx

                v1 = int(opcode[1], 16)
                v2 = int(opcode[2], 16)

                if self.Registers[v2].value > self.Registers[v1].value:
                    self.Registers[0xf].value = 1
                else:
                    self.Registers[0xf].value = 0

                self.Registers[v1].value = (self.Registers[v2].value - self.Registers[v1].value) & 255

            elif opcode[3] == 'e':
                #8XYE
                #Vx<<=1

                v1 = int(opcode[1], 16)
#                mostBit = int(bin(self.Registers[v1].value)[2])
                mostBit = (self.Registers[v1].value & 128) >> 7

                self.Registers[v1].value = (self.Registers[v1].value << 1) & 255
                self.Registers[0xf].value = mostBit
        
        elif opcode[0] == '9':
            #9XY0
            #if(Vx!=Vy)

            v1 = int(opcode[1], 16)
            v2 = int(opcode[2], 16)

            if self.Registers[v1].value != self.Registers[v2].value:
                self.ProgramCounter += 2
        
        elif opcode[0] == 'a':
            #ANNN
            #I = NNN

            addr = int(opcode[1:], 16)

            self.IRegister.value = addr
        
        elif opcode[0] == 'b':
            #BNNN
            #PC=V0+NNN

            addr = int(opcode[1:], 16)

            self.ProgramCounter = self.Registers[0].value + addr - 2
        
        elif opcode[0] == 'c':
            #CXNN
            #Vx=rand()&NN

            vNum = int(opcode[1], 16)
            targetNum = int(opcode[2:], 16)

            rand = urandom.randint(0, 255)

            self.Registers[vNum].value = targetNum & rand
        
        elif opcode[0] == 'd':
            #DXYN
            #draw(Vx,Vy,N)
            
            Vx = int(opcode[1], 16)
            Vy = int(opcode[2], 16)
            N  = int(opcode[3], 16)

            addr = self.IRegister.value
            sprite = self.Memory[addr: addr + N]

            for i in range(len(sprite)):
                if type(sprite[i]) == str:
                     sprite[i] = int(sprite[i], 16)

            if self.draw(self.Registers[Vx].value, self.Registers[Vy].value, sprite):
                self.Registers[0xf].value = 1
            else:
                self.Registers[0xf].value = 0
        
        elif opcode[0] == 'e':
            if opcode[2:] == '9e':
                #EX9E
                #if(key()==Vx)

                Vx = int(opcode[1], 16)
                key = self.Registers[Vx].value
                if self.keys[key]:
                    self.ProgramCounter += 2

            elif opcode[2:] == 'a1':
                #EXA1
                #if(key()!=Vx)

                Vx = int(opcode[1], 16)
                key = self.Registers[Vx].value
                if not self.keys[key]:
                    self.ProgramCounter += 2
        
        elif opcode[0] == 'f':
            if opcode[2:] == '07':
                #FX07
                #delay_timer(Vx)

                Vx = int(opcode[1], 16)
                self.Registers[Vx].value = self.delayTimer.readTimer()

            elif opcode[2:] == '0a':
                #FX0A
                #Vx = get_key()

                Vx = int(opcode[1], 16)
                key = None

                while True:
                    self.keyHandler()
                    isKeyDown = False

                    for i in range(len(self.keys)):
                        if self.keys[i]:
                            key = i
                            isKeyDown = True
                    
                    if isKeyDown:
                        break
                
                self.Registers[Vx].value = key
            
            elif opcode[2:] == '15':
                #FX15
                #delay_timer(Vx)

                Vx = int(opcode[1], 16)
                value = self.Registers[Vx].value

                self.delayTimer.setTimer(value)
            
            elif opcode[2:] == '18':
                #FX18
                #sound_timer(Vx)

                Vx = int(opcode[1], 16)
                value = self.Registers[Vx].value

                self.soundTimer.setTimer(value)
            
            elif opcode[2:] == '1e':
                #FX1E
                #I += Vx

                Vx = int(opcode[1], 16)
                self.IRegister.value += self.Registers[Vx].value
            
            elif opcode[2:] == '29':
                #FX29
                #I = sprite_addr[Vx]

                Vx = int(opcode[1], 16)
                value = self.Registers[Vx].value

                self.IRegister.value = value * 5
            
            elif opcode[2:] == '33':
                #FX33
                '''
                set_BCD(Vx);
                *(I+0)=BCD(3);
                *(I+1)=BCD(2);
                *(I+2)=BCD(1);
                '''

                Vx = int(opcode[1], 16)
                value = str(self.Registers[Vx].value)

                fillNum = 3 - len(value)
                value = '0' * fillNum + value

                for i in range(len(value)):
                    self.Memory[self.IRegister.value + i] = int(value[i])
            
            elif opcode[2:] == '55':
                #FX55
                #reg_dump(Vx, &I)

                Vx = int(opcode[1], 16)
                for i in range(0, Vx + 1):
                    self.Memory[self.IRegister.value + i] = self.Registers[i].value

            elif opcode[2:] == '65':
                #FX65
                #reg_load(Vx, &I)

                Vx = int(opcode[1], 16)
                for i in range(0, Vx + 1):
                    self.Registers[i].value = self.Memory[self.IRegister.value + i]

        self.ProgramCounter += 2

    def execution(self):
        pc = self.ProgramCounter

        opcode = '{:04x}'.format(self.Memory[pc]*256 + self.Memory[pc+1])

        self.execOpcode(opcode)

    def draw(self, Vx, Vy, sprite):
        collision = False

        spriteBits = []
        self.dirty = 1
        for i in sprite:
            binary = bin(i)
            line = list(binary[2:])
            fillNum = 8 - len(line)
            line = ['0'] * fillNum + line

            spriteBits.append(line)
        
        '''
        for i in spriteBits:
            print(i)
        '''

        for i in range(len(spriteBits)):
            #line = ''
            for j in range(8):
                try:
                    if self.grid[Vy + i][Vx + j] == 1 and int(spriteBits[i][j]) == 1:
                        collision = True

                    self.grid[Vy + i][Vx + j] = self.grid[Vy + i][Vx + j] ^ int(spriteBits[i][j])
                    #line += str(int(spriteBits[i][j]))
                except:
                    continue

            #print(line)
        
        return collision
    
    def clear(self):
        for i in range(len(self.grid)):
            for j in range(len(self.grid[0])):
                self.grid[i][j] = 0

    def readProg(self, filename):
        v = memoryview(self.Memory)
        rom = v[512:]
        with open(filename, 'rb') as f:
            f.readinto(rom)
    
    def convertProg(self, filename):
        rom = []

        with open(filename, 'rb') as f:
            wholeProgram = f.read()
            for i in wholeProgram:
                opcode = ord(i)
                rom.append(opcode)
        return rom
    
    def hexHandler(self, Num):
        print("hexHandler: Num: ",Num, " Type: ", type(Num))
        newHex = hex(Num)[2:]
        if len(newHex) == 1:
            newHex = '0' + newHex
        
        return newHex

    def keyHandler(self):
        '''
        Chip8       My Keys
        ---------   ---------
        1 2 3 C     7 8 9 /
        4 5 6 D     4 5 6 *
        7 8 9 E     1 2 3 -
        A 0 B F     0 . _ +
        '''

        key = hpprime.keyboard()

        if key & (1 << 4): # ESC
            sys.exit(0)

        if key & (1 << 41): # SHIFT
            if self.delay < 20:
                self.delay = 100
            else:
                if self.emu:
                  self.delay = 15
                else:
                  self.delay = 2

        if key & (1 << 19): # BSP
            self.reset()

        if key & (1 << 30): # ENTER
            hpprime.eval("wait(0)")

        if key & (1 << 16): # C
            self.dirty = 1
            if self.zeroColor == 0xffffff:
                self.oneColor = 0xffffff  # white
                self.zeroColor = 0x000000  # black
            else:
                self.oneColor = 0x0000ff  # blue
                self.zeroColor = 0xffffff  # white

        for k in self.keyDict.keys(): # CHIP-8 4x4 keypad
            if key & (1 << k):
                self.keys[self.keyDict[k]] = True
            else:
                self.keys[self.keyDict[k]] = False

        self.ticks = self.ticks + 1
        if self.ticks > self.delay:
            self.ticks = 0
            self.delayTimer.countDown()
        if self.emu:
            for k in range(1,15000): pass

    def reset(self):
        self.ProgramCounter = 0x200
        if self.emu:
          self.delay = 15
        else:
          self.delay = 2
        self.clear()

    def mainLoop(self):

        while True:
            self.keyHandler()
            self.soundTimer.beep()
            self.execution()
            self.display()

    
    def display(self):
        if not self.dirty:
            return
        for i in range(0, len(self.grid)):
            for j in range(0, len(self.grid[0])):
                cellColor = self.zeroColor

                if self.grid[i][j] == 1:
                    cellColor = self.oneColor
                
                rPixon5(j, i, cellColor)
        self.dirty = 0

#ticks = 0

def rCls() : graphic.clear_screen(0xffffff); hpprime.eval("print")

def rPixon5 (x,y, colour) :
    y = y * 5 + 20
    x = x * 5
    hpprime.fillrect(0,x,y,5, 5, colour, colour);

def rLastkey () : return int(hpprime.eval("getkey"))

def main():
    roms = []
    rCls()
    print("Prime CHIP8 1.0\n")
    files = hpprime.eval('AFiles')

    for fn in files:
        if fn.lower().endswith('.ch8'):
            roms.append(fn)

    if not roms:
        print("\nNo ROMs loaded. Press any key to exit...")
        hpprime.eval("wait(0)")
        return

    for fn in roms:
        print(roms.index(fn)," : ",fn)
    while True:
        try:    
            choice = int(input("\nChoose a ROM:"))
            if choice >= 0 and choice < len(roms):
                break
            else:
                print("\nInvalid selection...")
                continue
        except:
            print("\nInvalid selection...")

    hpprime.eval('wait(0.25)')
    chip8 = Emulator()
    try:
        chip8.readProg(roms[choice])
    except:
        print("\nROM error. Press any key to exit...")
        return

    print(roms[choice])
    rCls()
    chip8.mainLoop()

if __name__ == "__main__" : main()
#END
EXPORT CHIP8()
BEGIN
PYTHON(name);
END;