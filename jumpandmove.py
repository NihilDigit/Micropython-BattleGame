import hzckUtil
import FileUtil as fu
import machine
import time
import math
from BNST7735Driver import BNST7735Driver, BNColor
from BN165DKBDriver import keyCode
from machine import Pin

# ST7735 Init
bnsd = BNST7735Driver(4, 48, 5, 2)

# KeyPad Init
CP = Pin(41, Pin.OUT)
CE = Pin(39, Pin.OUT)
PL = Pin(40, Pin.OUT)
Q7 = Pin(21, Pin.IN)
adcIn = (CP, CE, PL, Q7)

# Position Init
h = 30
w = 10
screen_height = 128  # 屏幕高度
screen_width = 160   # 屏幕宽度

class Vec2d:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, other):
        return Vec2d(self.x + other.x, self.y + other.y)

    def __iadd__(self, other):
        self.x += other.x
        self.y += other.y
        return self

    def __mul__(self, scalar):
        return Vec2d(self.x * scalar, self.y * scalar)

    def __imul__(self, scalar):
        self.x *= scalar
        self.y *= scalar
        return self

class Player(Vec2d):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.velocity = Vec2d(0, 0)
        self.gravity = 0.5
        self.on_ground = True
        self.jump_velocity = -10  # 跳跃初速度
        self.move_speed = 5       # 平移速度

    def jump(self):
        if self.on_ground:
            self.velocity.y = self.jump_velocity
            self.on_ground = False

    def update_jump(self, dt):
        if not self.on_ground:
            # 计算位移
            self.velocity.y += self.gravity  # 模拟重力加速度
            self += self.velocity * dt  # 根据速度和时间更新位置

            # 检测是否着地
            if self.y >= screen_height - h:  # 地面 Y 坐标为屏幕高度减去玩家高度
                self.on_ground = True
                self.y = screen_height - h  # 确保刚好落在地面
                self.velocity.y = 0

    def update_movement(self, dt):
        # 处理左右平移
        kc = keyCode(adcIn)
        if kc == 1:  # 向左移动
            self.x -= self.move_speed * dt
        elif kc == 3:  # 向右移动
            self.x += self.move_speed * dt

        # 检测是否超出屏幕边界
        if self.x < 0:
            self.x = 0
        elif self.x > screen_width - w:
            self.x = screen_width - w

player = Player(50, screen_height - h)  # 初始化玩家位置在地面上
last_time = time.ticks_ms()

while True:
    kc = keyCode(adcIn)
    if kc == 0:
        print("Pressed")
        player.jump()
    dt = time.ticks_diff(time.ticks_ms(), last_time) / 1000
    player.update_jump(dt)
    player.update_movement(dt)
    last_time = time.ticks_ms()
    bnsd.clear(bnsd.BNcolor(0, 0, 0))
    bnsd.drawRect(int(player.x), int(player.y), w, h, bnsd.BNcolor(255, 100, 100), True)  # 绘制角色
    bnsd.show()
