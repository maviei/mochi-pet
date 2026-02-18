# MochiPet v2.0 - BitDogLab v6.3 (MicroPython)
# Virtual Pet para Raspberry Pi Pico W
import gc
gc.collect()
import time, json, math, random, network, ntptime, machine
from micropython import const
from machine import Pin, PWM, ADC, SoftI2C
from neopixel import NeoPixel
from ssd1306 import SSD1306_I2C
gc.collect()

# ============================================================
# SECTION 1: HARDWARE
# ============================================================
i2c = SoftI2C(scl=Pin(15), sda=Pin(14))
oled = SSD1306_I2C(128, 64, i2c)
np = NeoPixel(Pin(7), 25)
led_r = PWM(Pin(13)); led_r.freq(1000); led_r.duty_u16(0)
led_g = PWM(Pin(11)); led_g.freq(1000); led_g.duty_u16(0)
led_b = PWM(Pin(12)); led_b.freq(1000); led_b.duty_u16(0)
buzzer = PWM(Pin(21)); buzzer.freq(1000); buzzer.duty_u16(0)
btn_a = Pin(5, Pin.IN, Pin.PULL_UP)
btn_b = Pin(6, Pin.IN, Pin.PULL_UP)
btn_joy = Pin(22, Pin.IN, Pin.PULL_UP)
joy_x = ADC(Pin(26))
joy_y = ADC(Pin(27))
mic = ADC(Pin(28))
gc.collect()

# ============================================================
# SECTION 2: CONFIG + PERSISTENCE
# ============================================================
CFG = {"som": True, "vol": 1, "noturno": "auto", "hr_dormir": 22,
       "hr_acordar": 8, "brilho": 1, "mic_reage": True,
       "neo_efeitos": True, "tz": -3, "humor": 4, "skin": 0}
VOL = (1000, 5000, 15000)
BRILHO = (8, 20, 50)
NOT_MODES = ("auto", "ligado", "desligado")
emotions = {"happy": 75, "hunger": 85, "energy": 90, "fun": 60}
stats = {"i": 0, "g": 0, "f": 0, "m": 0, "ep": 0}

def load_state():
    try:
        with open("config.json", "r") as f:
            d = json.load(f)
        if d.get("v") == 2:
            for k in CFG:
                if k in d.get("cfg", {}):
                    CFG[k] = d["cfg"][k]
            for k in emotions:
                if k in d.get("emo", {}):
                    emotions[k] = d["emo"][k]
            for k in stats:
                if k in d.get("st", {}):
                    stats[k] = d["st"][k]
    except:
        pass

def save_state():
    if tem_relogio:
        t = time.localtime()
        stats["ep"] = time.mktime(t) + CFG["tz"] * 3600
    try:
        with open("config.json", "w") as f:
            json.dump({"v": 2, "cfg": CFG, "emo": emotions, "st": stats}, f)
    except Exception as e:
        print("Save err:", e)

load_state()
gc.collect()

# ============================================================
# SECTION 3: WIFI + NTP
# ============================================================
WIFI_SSID = "SUA_REDE_WIFI"
WIFI_PASS = "SUA_SENHA_WIFI"
wlan = None
wifi_ok = False
tem_relogio = False
hora_atual = 12
minuto_atual = 0

def wifi_connect():
    global wlan, wifi_ok
    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        if wlan.isconnected():
            wifi_ok = True
            return True
        wlan.connect(WIFI_SSID, WIFI_PASS)
        t0 = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), t0) > 10000:
                wifi_ok = False
                return False
            time.sleep_ms(100)
        wifi_ok = True
        print("WiFi OK:", wlan.ifconfig()[0])
        return True
    except Exception as e:
        print("WiFi err:", e)
        wifi_ok = False
        return False

def ntp_sync():
    global tem_relogio
    if not wifi_ok:
        return False
    for srv in ("pool.ntp.org", "time.google.com"):
        try:
            ntptime.host = srv
            ntptime.settime()
            tem_relogio = True
            update_clock()
            print("NTP OK (%s): %02d:%02d" % (srv, hora_atual, minuto_atual))
            return True
        except:
            continue
    print("NTP: todos falharam")
    return False

def update_clock():
    global hora_atual, minuto_atual
    if not tem_relogio:
        return
    t = time.localtime()
    epoch = time.mktime(t) + CFG["tz"] * 3600
    local = time.localtime(epoch)
    hora_atual = local[3]
    minuto_atual = local[4]

def is_noite():
    if CFG["noturno"] == "ligado":
        return True
    if CFG["noturno"] == "desligado":
        return False
    if not tem_relogio:
        return False
    hd = CFG["hr_dormir"]
    ha = CFG["hr_acordar"]
    if hd > ha:
        return hora_atual >= hd or hora_atual < ha
    return hora_atual >= hd and hora_atual < ha

gc.collect()

# ============================================================
# SECTION 4: SOUND
# ============================================================
def beep(freq=1000, dur=50):
    if not CFG["som"] or is_noite():
        return
    buzzer.freq(int(freq))
    buzzer.duty_u16(VOL[CFG["vol"]])
    time.sleep_ms(dur)
    buzzer.duty_u16(0)

def play_melody(notes):
    if not CFG["som"] or is_noite():
        return
    for f, d in notes:
        if f > 0:
            buzzer.freq(int(f))
            buzzer.duty_u16(VOL[CFG["vol"]])
        else:
            buzzer.duty_u16(0)
        time.sleep_ms(d)
    buzzer.duty_u16(0)

M_HAPPY  = ((523,100),(659,100),(784,150),(1047,250))
M_EAT    = ((523,50),(0,50),(523,50),(0,50),(659,50),(0,50),(523,100))
M_LOVE   = ((523,150),(659,150),(784,150),(880,300))
M_WAKE   = ((262,100),(330,100),(392,100),(523,200))
M_SLEEP  = ((392,300),(330,300),(262,500))
M_SCARED = ((988,50),(0,50),(988,50),(880,50),(784,100))
M_CHIRP  = ((1319,40),(1175,40),(1319,40))
M_GS     = ((523,80),(587,80),(659,80),(784,150))
M_GW     = ((523,80),(659,80),(784,80),(1047,80),(784,80),(1047,300))
M_GL     = ((392,150),(349,150),(330,150),(294,300))

MUSIC_LIST = (
    ("Star Wars", ((440,250),(440,250),(440,250),(349,187),(523,62),(440,250),
                   (349,187),(523,62),(440,500),(659,250),(659,250),(659,250),
                   (698,187),(523,62),(415,250),(349,187),(523,62),(440,500))),
    ("Parabens",  ((262,125),(262,125),(294,250),(262,250),(349,250),(330,500),
                   (262,125),(262,125),(294,250),(262,250),(392,250),(349,500))),
    ("Nokia",     ((659,125),(587,125),(370,250),(415,250),(554,125),(494,125),
                   (294,250),(330,250),(494,125),(440,125),(277,250),(330,250),
                   (440,500))),
)

def play_music(idx):
    if idx < 0 or idx >= len(MUSIC_LIST):
        return
    for f, d in MUSIC_LIST[idx][1]:
        if f > 0:
            buzzer.freq(f)
            buzzer.duty_u16(VOL[CFG["vol"]] if CFG["som"] else 0)
        else:
            buzzer.duty_u16(0)
        time.sleep_ms(d)
        if btn_b.value() == 0:
            buzzer.duty_u16(0)
            return
    buzzer.duty_u16(0)

gc.collect()

# ============================================================
# SECTION 5: LED SYSTEMS
# ============================================================
_bs = BRILHO[CFG["brilho"]]

def _sc(r, g, b):
    return (r * _bs >> 8, g * _bs >> 8, b * _bs >> 8)

def rgb(r, g, b):
    if is_noite():
        r, g, b = r >> 2, g >> 2, b >> 2
    led_r.duty_u16(r * 257)
    led_g.duty_u16(g * 257)
    led_b.duty_u16(b * 257)

def rgb_off():
    led_r.duty_u16(0)
    led_g.duty_u16(0)
    led_b.duty_u16(0)

def update_need_led():
    if emotions["hunger"] < 25:
        rgb(180, 0, 0)
    elif emotions["energy"] < 20:
        rgb(0, 0, 180)
    elif emotions["fun"] < 20:
        rgb(180, 180, 0)
    elif emotions["happy"] < 25:
        rgb(150, 0, 150)
    else:
        rgb_off()

HEART = (0,0,1,0,0, 0,1,1,1,0, 1,1,1,1,1, 1,1,1,1,1, 0,1,0,1,0)
_LED_M = ((0,1,2,3,4),(9,8,7,6,5),(10,11,12,13,14),(19,18,17,16,15),(20,21,22,23,24))

def neo_xy(x, y):
    return _LED_M[y][x]

def neo_clear():
    for i in range(25):
        np[i] = (0, 0, 0)
    np.write()

def neo_fill(c):
    sc = _sc(*c)
    for i in range(25):
        np[i] = sc
    np.write()

def neo_pattern(pat, c):
    sc = _sc(*c)
    for i in range(25):
        np[i] = sc if pat[i] else (0, 0, 0)
    np.write()

def neo_rainbow(offset):
    for i in range(25):
        h = (i * 10 + offset) % 256
        r = max(0, 255 - abs(h - 85) * 3)
        g = max(0, 255 - abs(h - 170) * 3)
        b = max(0, 255 - abs(h) * 3)
        np[i] = _sc(r, g, b)
    np.write()

def neo_breathe(c, phase):
    b = int((math.sin(phase) + 1) * 0.5 * _bs)
    col = (c[0] * b >> 8, c[1] * b >> 8, c[2] * b >> 8)
    for i in range(25):
        np[i] = col
    np.write()

gc.collect()

# ============================================================
# SECTION 5B: TINY CLOCK FONT
# ============================================================
_TF = ((7,5,5,5,7),(2,6,2,2,7),(7,1,7,4,7),(7,1,7,1,7),(5,5,7,1,1),
       (7,4,7,1,7),(7,4,7,5,7),(7,1,1,1,1),(7,5,7,5,7),(7,5,7,1,7))

def draw_clock(x, y):
    if not tem_relogio:
        return
    for d in (hora_atual // 10, hora_atual % 10, -1, minuto_atual // 10, minuto_atual % 10):
        if d == -1:
            oled.pixel(x, y + 1, 1)
            oled.pixel(x, y + 3, 1)
            x += 2
            continue
        g = _TF[d]
        for row in range(5):
            bits = g[row]
            if bits & 4: oled.pixel(x, y + row, 1)
            if bits & 2: oled.pixel(x + 1, y + row, 1)
            if bits & 1: oled.pixel(x + 2, y + row, 1)
        x += 4

# ============================================================
# SECTION 6: FACE RENDERING
# ============================================================
EXPR_NORMAL   = const(0)
EXPR_HAPPY    = const(1)
EXPR_SAD      = const(2)
EXPR_SLEEPY   = const(4)
EXPR_SURPRISED= const(5)
EXPR_LOVE     = const(6)
EXPR_EXCITED  = const(7)
EXPR_SCARED   = const(8)
EXPR_EATING   = const(9)

def fill_circle(cx, cy, r, c=1):
    for dy in range(-r, r + 1):
        hw = int(math.sqrt(max(0, r * r - dy * dy)))
        oled.fill_rect(cx - hw, cy + dy, hw * 2 + 1, 1, c)

def circle(cx, cy, r, c=1):
    x, y, err = r, 0, 1 - r
    while x >= y:
        for px, py in ((cx+x,cy+y),(cx-x,cy+y),(cx+x,cy-y),(cx-x,cy-y),
                        (cx+y,cy+x),(cx-y,cy+x),(cx+y,cy-x),(cx-y,cy-x)):
            if 0 <= px < 128 and 0 <= py < 64:
                oled.pixel(px, py, c)
        y += 1
        if err < 0:
            err += 2 * y + 1
        else:
            x -= 1
            err += 2 * (y - x) + 1

def draw_eyes(cx_l, cx_r, cy, r, pr, expr, lx, ly, bp):
    mm = r - pr - 2
    plx = max(-mm, min(mm, lx * 2))
    ply = max(-mm, min(mm, ly * 2))
    for ecx in (cx_l, cx_r):
        if expr == EXPR_LOVE:
            for hy in range(-r, r + 1):
                for hx in range(-r, r + 1):
                    fx, fy = hx / r, hy / r
                    if (fx*fx + fy*fy - 1)**3 - fx*fx * fy*fy*fy <= 0:
                        oled.pixel(ecx + hx, cy + hy, 1)
        elif expr in (EXPR_HAPPY, EXPR_EATING) and bp > 0.3:
            for ang in range(0, 181, 5):
                rad = ang * 0.01745
                px = ecx + int(r * math.cos(rad))
                py = cy - int(r * 0.5 * math.sin(rad))
                if 0 <= px < 128 and 0 <= py < 64:
                    oled.pixel(px, py, 1)
                    if py + 1 < 64:
                        oled.pixel(px, py + 1, 1)
            oled.hline(ecx - r, cy, r * 2, 1)
        elif expr == EXPR_SLEEPY:
            for i in range(-r, r + 1):
                t = i / r
                cv = int(2 * (1 - t * t))
                oled.pixel(ecx + i, cy + cv, 1)
                oled.pixel(ecx + i, cy + cv - 1, 1)
        elif bp < 0.15:
            oled.hline(ecx - r, cy, r * 2, 1)
            oled.hline(ecx - r, cy - 1, r * 2, 1)
        else:
            sk = CFG["skin"]
            if sk == 2:
                oled.fill_rect(ecx - r, cy - r, r * 2, r * 2, 1)
                oled.fill_rect(ecx + plx - pr, cy + ply - pr, pr * 2, pr * 2, 0)
                oled.fill_rect(ecx + plx - pr + 1, cy + ply - pr + 1, 2, 2, 1)
            elif sk == 3:
                fill_circle(ecx, cy, r, 1)
                pw = max(2, pr // 2)
                oled.fill_rect(ecx + plx - pw // 2, cy + ply - pr, pw, pr * 2, 0)
                oled.pixel(ecx + plx - pw, cy + ply - pr + 1, 1)
            else:
                fill_circle(ecx, cy, r, 1)
                apr = pr + 1 if sk == 1 else pr
                fill_circle(ecx + plx, cy + ply, apr, 0)
                bx = ecx + plx - pr // 2 - 1
                by = cy + ply - pr // 2 - 1
                oled.pixel(bx, by, 1)
                oled.pixel(bx + 1, by, 1)
                oled.pixel(bx, by + 1, 1)
                oled.pixel(bx + 1, by + 1, 1)
                if sk == 1:
                    oled.pixel(bx + 2, by, 1)
                    oled.pixel(bx, by + 2, 1)
                oled.pixel(ecx + plx + pr // 2, cy + ply + pr // 2 - 1, 1)

def draw_face(expr, lx=0, ly=0, bp=1.0):
    oled.fill(0)
    R, PR, blush = 14, 5, False
    if expr == EXPR_HAPPY:
        blush = True
    elif expr == EXPR_SAD:
        ly = max(ly, 2); PR = 6
    elif expr == EXPR_SURPRISED:
        R = 17; PR = 3
    elif expr == EXPR_LOVE:
        blush = True
    elif expr == EXPR_EXCITED:
        R = 16; PR = 4; blush = True
    elif expr == EXPR_SCARED:
        R = 16; PR = 2; lx = max(lx, 2)
    elif expr == EXPR_EATING:
        blush = True
    elif expr == EXPR_SLEEPY:
        R = 12
    draw_eyes(38, 90, 24, R, PR, expr, lx, ly, bp)
    sk = CFG["skin"]
    mx, my = 64, 50
    if expr in (EXPR_HAPPY, EXPR_EXCITED, EXPR_EATING):
        if sk == 2:
            oled.fill_rect(mx - 8, my + 2, 16, 3, 1)
            oled.fill_rect(mx - 6, my + 5, 12, 2, 1)
        elif sk == 3:
            for i in range(-8, 9):
                t = i / 8
                oled.pixel(mx + i, my + 4 - int(3 * (1 - t * t)), 1)
        else:
            w = 12 if sk == 1 else 10
            for i in range(-w, w + 1):
                t = i / w
                cy_m = int(5 * (1 - t * t))
                oled.pixel(mx + i, my + 5 - cy_m, 1)
            if sk == 1:
                fill_circle(mx, my + 4, 4, 1)
        if expr == EXPR_EATING:
            fill_circle(mx, my + 5, 3, 1)
    elif expr in (EXPR_SAD, EXPR_SCARED):
        if sk == 2:
            oled.fill_rect(mx - 6, my - 1, 12, 2, 1)
        else:
            for i in range(-7, 8):
                t = i / 7
                cy_m = int(3 * (1 - t * t))
                oled.pixel(mx + i, my - 2 + cy_m, 1)
    elif expr == EXPR_SURPRISED:
        if sk == 2:
            oled.rect(mx - 4, my - 1, 8, 8, 1)
        else:
            circle(mx, my + 2, 5, 1)
    elif expr == EXPR_SLEEPY:
        if sk == 2:
            oled.fill_rect(mx - 3, my, 6, 2, 1)
        else:
            circle(mx, my + 2, 4, 1)
        oled.text("z", 108, 3, 1)
        oled.text("Z", 116, 0, 1)
    else:
        if sk == 1:
            for i in (-3, -1, 1, 3):
                oled.pixel(mx + i, my + (1 if abs(i) == 1 else 0), 1)
            oled.pixel(mx, my + 2, 1)
        elif sk == 2:
            oled.hline(mx - 5, my, 4, 1)
            oled.hline(mx + 1, my, 4, 1)
        elif sk == 3:
            oled.pixel(mx, my, 1)
            oled.pixel(mx + 1, my + 1, 1)
            oled.pixel(mx, my + 2, 1)
            oled.pixel(mx + 1, my + 3, 1)
            oled.pixel(mx, my + 4, 1)
        else:
            oled.hline(mx - 4, my, 8, 1)
    if sk == 3:
        for i in range(3):
            wy = 33 + i * 4
            oled.hline(10, wy, 16, 1)
            oled.hline(102, wy, 16, 1)
        if tongue_out and expr not in (EXPR_SLEEPY, EXPR_EATING, EXPR_SURPRISED):
            ty = my + 6 if expr in (EXPR_HAPPY, EXPR_EXCITED) else my + 5
            oled.fill_rect(mx - 1, ty, 3, 4, 1)
            oled.pixel(mx - 1, ty + 3, 0)
            oled.pixel(mx + 1, ty + 3, 0)
    elif blush or sk == 1:
        for dy in range(-1, 2):
            for dx in range(0, 5):
                oled.pixel(17 + dx * 2, 36 + dy, 1)
                oled.pixel(103 + dx * 2, 36 + dy, 1)
    draw_clock(1, 1)
    oled.show()

def draw_face_msg(expr, msg, lx=0, ly=0, bp=1.0):
    oled.fill(0)
    R, PR = 10, 4
    if expr == EXPR_SAD:
        ly = max(ly, 1); PR = 5
    elif expr == EXPR_SURPRISED:
        R = 12; PR = 2
    elif expr == EXPR_SLEEPY:
        R = 8
    draw_eyes(38, 90, 16, R, PR, expr, lx, ly, bp)
    mx = 64
    my = 32
    if expr in (EXPR_HAPPY, EXPR_EXCITED, EXPR_EATING):
        for i in range(-6, 7):
            t = i / 6
            cy_m = int(3 * (1 - t * t))
            oled.pixel(mx + i, my + 3 - cy_m, 1)
    elif expr in (EXPR_SAD, EXPR_SCARED):
        for i in range(-5, 6):
            t = i / 5
            cy_m = int(2 * (1 - t * t))
            oled.pixel(mx + i, my - 1 + cy_m, 1)
    elif expr == EXPR_SLEEPY:
        oled.text("z", 110, 2, 1)
        oled.text("Z", 118, 0, 1)
        circle(mx, my + 1, 3, 1)
    else:
        oled.hline(mx - 3, my, 6, 1)
    oled.hline(0, 38, 128, 1)
    if len(msg) <= 15:
        oled.text(msg, max(0, 64 - len(msg) * 4), 44, 1)
    else:
        oled.text(msg[:15], 2, 42, 1)
        oled.text(msg[15:30], 2, 52, 1)
    draw_clock(1, 1)
    oled.show()

def draw_text_only(title, lines):
    oled.fill(0)
    oled.text(title[:16], max(0, 64 - len(title[:16]) * 4), 0, 1)
    oled.hline(0, 10, 128, 1)
    for i, line in enumerate(lines):
        if i > 4:
            break
        oled.text(line[:15], 2, 14 + i * 11, 1)
    draw_clock(111, 1)
    oled.show()

gc.collect()

# ============================================================
# SECTION 7: INPUT
# ============================================================
prev_a = 1
prev_b = 1
prev_j = 1
last_a_tap = 0
last_b_tap = 0
_mic_buf = [0] * 8

def read_joy():
    x = (joy_y.read_u16() - 32768) * 100 // 32768
    y = -((joy_x.read_u16() - 32768) * 100 // 32768)
    return x, y

def read_mic():
    for i in range(8):
        _mic_buf[i] = mic.read_u16()
    return max(_mic_buf) - min(_mic_buf)

def get_joy_dir(x, y):
    if abs(x) < 20 and abs(y) < 20:
        return "none"
    if abs(x) > abs(y):
        return "right" if x > 0 else "left"
    return "down" if y > 0 else "up"

gc.collect()

# ============================================================
# SECTION 8: EMOTION ENGINE + PET LOGIC
# ============================================================
pet_state = "idle"
react_end = 0
last_decay = time.ticks_ms()
last_interact = time.ticks_ms()
sleep_mode_active = False
manual_sleep = False
wake_count = 0
drowsy_stir = 0
last_dream = 0
next_dream = time.ticks_ms() + 60000
dream_msg = ""
last_fed_time = time.ticks_ms()
last_game_time = time.ticks_ms()
next_hunger = time.ticks_ms() + random.randint(1800000, 3600000)
next_energy = time.ticks_ms() + random.randint(1200000, 2700000)
next_fun = time.ticks_ms() + random.randint(1500000, 3000000)
talk_msg = ""
talk_mode = 0
last_talk = time.ticks_ms() + 10000
last_gracinha = time.ticks_ms()
next_gracinha = random.randint(300000, 600000)
blink_timer = time.ticks_ms() + random.randint(3000, 7000)
is_blinking = False
blink_start = 0
tongue_out = False
tongue_timer = time.ticks_ms() + random.randint(12000, 30000)
tongue_start = 0
look_x = 0
look_y = 0

_HUMOR_T = ((80, 70, -1), (50, 30, -1), (45, 50, 40), (70, 90, 80))
_humor_rand = random.randint(0, 3)
_humor_next = 0
_base_mins = 0
_session_start = time.ticks_ms()

def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))

def decay_emotions():
    global last_decay, next_hunger, next_energy, next_fun
    global _humor_rand, _humor_next, _base_mins
    now = time.ticks_ms()
    if time.ticks_diff(now, last_decay) < 30000:
        return
    last_decay = now
    stats["m"] = _base_mins + time.ticks_diff(now, _session_start) // 60000
    if pet_state in ("sleeping", "drowsy"):
        emotions["energy"] = clamp(emotions["energy"] + 2)
    elif is_noite():
        emotions["energy"] = clamp(emotions["energy"] + 1)
    else:
        if time.ticks_diff(now, next_hunger) >= 0:
            emotions["hunger"] = clamp(emotions["hunger"] - 1)
            next_hunger = now + random.randint(1800000, 3600000)
        if time.ticks_diff(now, next_energy) >= 0:
            emotions["energy"] = clamp(emotions["energy"] - 1)
            next_energy = now + random.randint(1200000, 2700000)
        if time.ticks_diff(now, next_fun) >= 0:
            emotions["fun"] = clamp(emotions["fun"] - 1)
            next_fun = now + random.randint(1500000, 3000000)
    avg = (emotions["hunger"] + emotions["energy"] + emotions["fun"]) // 3
    if emotions["happy"] < avg:
        emotions["happy"] = min(emotions["happy"] + 1, 100)
    elif emotions["happy"] > avg:
        emotions["happy"] = max(emotions["happy"] - 1, 0)
    # Humor influence
    h = CFG["humor"]
    if h == 4:
        if time.ticks_diff(now, _humor_next) >= 0:
            _humor_rand = random.randint(0, 3)
            _humor_next = now + random.randint(3600000, 10800000)
        h = _humor_rand
    if h < 4:
        ht, ft, et = _HUMOR_T[h]
        if emotions["happy"] < ht:
            emotions["happy"] = min(emotions["happy"] + 1, 100)
        elif emotions["happy"] > ht + 15:
            emotions["happy"] = max(emotions["happy"] - 1, 0)
        if emotions["fun"] < ft:
            emotions["fun"] = min(emotions["fun"] + 1, 100)
        elif emotions["fun"] > ft + 15:
            emotions["fun"] = max(emotions["fun"] - 1, 0)
        if et >= 0:
            if emotions["energy"] < et:
                emotions["energy"] = min(emotions["energy"] + 1, 100)
            elif emotions["energy"] > et + 15:
                emotions["energy"] = max(emotions["energy"] - 1, 0)

AGE_NAMES = ("Filhote", "Jovem", "Adulto")
DREAMS = ("*comida*", "*parque*", "*voando*", "*doces*", "*estrelas*", "*musica*")

def get_age():
    m = stats["m"]
    if m < 4320:
        return 0
    if m < 10080:
        return 1
    return 2

def get_personality():
    f, g, i = stats["f"], stats["g"], stats["i"]
    if g > f and g > 5:
        return "competitivo"
    if f > g * 2 and f > 5:
        return "comilao"
    if i > g * 3 and i > f * 2 and i > 10:
        return "carinhoso"
    if g + f + i > 20:
        return "brincalhao"
    return "equilibrado"

FALAS_FOME = ("Fominha...", "Comida!")
FALAS_CANSADO = ("Sono...", "*boceja*")
FALAS_RANDOM = ("Hmm...", "Eu sou Mochi!", "*pula*", "Beep boop!", "*danca*", "Curioso!")
FALAS_SONO = ("Que barulho..", "*abre 1 olho*", "Shh dormindo.", "*vira pro lado*",
              "5 minutinhos.", "*ronca* zzz", "Para barulho!", "Deixa dormir!")

def get_expression():
    if pet_state in ("sleeping", "drowsy"):
        return EXPR_SLEEPY
    if pet_state == "eating":
        return EXPR_EATING
    if is_noite() and pet_state == "idle":
        return EXPR_SLEEPY
    if emotions["hunger"] < 20:
        return EXPR_SAD
    if emotions["energy"] < 15:
        return EXPR_SLEEPY
    h = CFG["humor"]
    if h == 4:
        h = _humor_rand
    if h == 0:
        if emotions["happy"] > 55:
            return EXPR_EXCITED
        if emotions["happy"] > 35:
            return EXPR_HAPPY
        return EXPR_NORMAL
    elif h == 1:
        if emotions["happy"] > 90:
            return EXPR_HAPPY
        if emotions["happy"] < 25:
            return EXPR_SAD
        return EXPR_NORMAL
    elif h == 2:
        if emotions["happy"] > 70:
            return EXPR_HAPPY
        if emotions["happy"] < 40:
            return EXPR_SCARED
        return EXPR_NORMAL
    elif h == 3:
        if emotions["happy"] > 45:
            return EXPR_EXCITED
        return EXPR_SURPRISED
    if emotions["happy"] > 80:
        return EXPR_EXCITED
    if emotions["happy"] > 60:
        return EXPR_HAPPY
    if emotions["happy"] < 20:
        return EXPR_SAD
    return EXPR_NORMAL

gc.collect()

# ============================================================
# SECTION 9: PET ACTIONS
# ============================================================
def do_feed():
    global pet_state, react_end, last_interact, talk_msg, talk_mode, last_fed_time
    emotions["hunger"] = clamp(emotions["hunger"] + 30)
    emotions["happy"] = clamp(emotions["happy"] + 10)
    stats["f"] += 1
    stats["i"] += 1
    now = time.ticks_ms()
    last_interact = now
    last_fed_time = now
    talk_msg = random.choice(("Nom nom!", "NHAC!", "Hmmm bom!"))
    talk_mode = 0
    for i in range(4):
        draw_face(EXPR_EATING, 0, 2 if i % 2 else -1, 1.0)
        beep(470, 30)
        time.sleep_ms(250)
    if CFG["neo_efeitos"]:
        neo_pattern(HEART, (255, 130, 0))
    pet_state = "talking"
    react_end = time.ticks_ms() + 2000

def do_pet():
    global pet_state, react_end, last_interact, talk_msg, talk_mode
    emotions["happy"] = clamp(emotions["happy"] + 15)
    emotions["fun"] = clamp(emotions["fun"] + 5)
    stats["i"] += 1
    last_interact = time.ticks_ms()
    talk_msg = random.choice(("Prrrr.. <3", "*derretendo*", "Hehe para!"))
    talk_mode = 0
    e = random.choice((EXPR_HAPPY, EXPR_LOVE))
    for i in range(4):
        draw_face(e, random.randint(-2, 2), random.randint(-1, 1), 1.0)
        beep(600, 20)
        time.sleep_ms(200)
    if CFG["neo_efeitos"]:
        neo_pattern(HEART, (255, 30, 100))
    play_melody(M_LOVE)
    pet_state = "talking"
    react_end = time.ticks_ms() + 2000

def do_play():
    global pet_state, react_end, last_interact
    emotions["fun"] = clamp(emotions["fun"] + 20)
    emotions["energy"] = clamp(emotions["energy"] - 5)
    emotions["happy"] = clamp(emotions["happy"] + 10)
    stats["i"] += 1
    last_interact = time.ticks_ms()
    pet_state = "reacting"
    react_end = time.ticks_ms() + 2000
    play_melody(M_HAPPY)

def do_exercise():
    global pet_state, react_end, last_interact, talk_msg, talk_mode
    emotions["energy"] = clamp(emotions["energy"] - 10)
    emotions["fun"] = clamp(emotions["fun"] + 15)
    emotions["happy"] = clamp(emotions["happy"] + 5)
    emotions["hunger"] = clamp(emotions["hunger"] - 5)
    stats["i"] += 1
    last_interact = time.ticks_ms()
    X = ("Flexao!", "*correndo*", "Pula! ^o^", "Namaste~")
    talk_msg = random.choice(X)
    talk_mode = 0
    for i in range(5):
        draw_face(EXPR_EXCITED, random.randint(-3, 3), random.randint(-2, 2), 1.0)
        beep(random.randint(300, 700), 30)
        time.sleep_ms(300)
    if CFG["neo_efeitos"]:
        neo_rainbow(random.randint(0, 255))
    pet_state = "talking"
    react_end = time.ticks_ms() + 2000

def do_wake(irritated=False):
    global pet_state, react_end, talk_msg, talk_mode, sleep_mode_active, manual_sleep, wake_count, last_interact
    for b in (0.1, 0.4, 1.0):
        draw_face(EXPR_SLEEPY if b < 0.5 else EXPR_NORMAL, 0, 0, b)
        time.sleep_ms(200)
    oled.contrast(255)
    sleep_mode_active = False
    manual_sleep = False
    play_melody(M_WAKE)
    pet_state = "idle"
    last_interact = time.ticks_ms()
    if irritated:
        wake_count += 1
        W = ("Hm? To aqui!", "De novo?", "PARA acordar!")
        talk_msg = W[min(wake_count - 1, 2)]
        talk_mode = 0
        pet_state = "talking"
        react_end = time.ticks_ms() + 3000

def maybe_talk():
    global last_talk, talk_msg, talk_mode, pet_state, react_end
    now = time.ticks_ms()
    if time.ticks_diff(now, last_talk) < 25000 or pet_state != "idle" or is_noite():
        return
    last_talk = now
    if random.random() > 0.75:
        return
    msg = None
    talk_mode = 0
    if emotions["hunger"] < 15:
        talk_mode = 1
        draw_text_only("FOME!", ("Estomago", "roncando!", "", "A = comer"))
        pet_state = "talking"
        react_end = now + 5000
        return
    if emotions["energy"] < 10:
        talk_mode = 1
        draw_text_only("EXAUSTO!", ("Nao aguento...", "", "Menu > Dormir"))
        pet_state = "talking"
        react_end = now + 5000
        return
    if time.ticks_diff(now, last_interact) > 3600000 and random.random() < 0.5:
        msg = random.choice(("Esqueceu mim?", "To sozinho..", "Oi?? Alguem?"))
    elif time.ticks_diff(now, last_fed_time) > 5400000 and random.random() < 0.3:
        msg = "To com fominha.."
    elif time.ticks_diff(now, last_game_time) > 7200000 and random.random() < 0.3:
        msg = "Bora jogar?"
    elif emotions["hunger"] < 30:
        msg = random.choice(FALAS_FOME)
    elif emotions["energy"] < 25:
        msg = random.choice(FALAS_CANSADO)
    elif emotions["fun"] < 25:
        msg = random.choice(("Entediado..", "Jogar?"))
    elif emotions["happy"] < 25:
        msg = random.choice(("Triste...", "Atencao?"))
    elif emotions["happy"] > 75:
        msg = random.choice(("La la la!", "<3 feliz!"))
    else:
        a = get_age()
        p = get_personality()
        r = random.random()
        if a == 0 and r < 0.2:
            msg = random.choice(("Gugu!", "*baba*", "Aga!"))
        elif p[:3] == "com" and r < 0.3:
            msg = random.choice(("Cheirinho..", "Nhaam!"))
        elif p[:3] == "car" and r < 0.25:
            msg = random.choice(("Pertinho <3", "Carinho?"))
        elif r < 0.4:
            msg = random.choice(FALAS_RANDOM)
    if msg:
        talk_msg = msg
        pet_state = "talking"
        react_end = now + 3500

def do_gracinha():
    global pet_state, react_end, talk_msg, talk_mode, last_gracinha, next_gracinha
    last_gracinha = time.ticks_ms()
    next_gracinha = random.randint(300000, 600000)
    g = random.randint(0, 4)
    now = time.ticks_ms
    if g == 0:
        for _ in range(3):
            draw_face(EXPR_HAPPY, 0, 0, 1.0)
            oled.fill_rect(76, 10, 28, 28, 0)
            oled.hline(78, 24, 24, 1)
            oled.hline(78, 25, 24, 1)
            oled.show()
            beep(800, 30)
            time.sleep_ms(400)
            draw_face(EXPR_HAPPY, 0, 0, 1.0)
            time.sleep_ms(300)
        talk_msg = "~_^ Piscadinha!"
    elif g == 1:
        for _ in range(6):
            ox = random.randint(-4, 4)
            oy = random.randint(-2, 2)
            draw_face(EXPR_EXCITED, ox, oy, 1.0)
            beep(random.randint(400, 1200), 30)
            time.sleep_ms(250)
        if CFG["neo_efeitos"]:
            neo_rainbow(random.randint(0, 255))
            time.sleep_ms(500)
        talk_msg = "*danca* ^o^"
    elif g == 2:
        draw_face(EXPR_SCARED, 3, 0, 1.0)
        beep(988, 100)
        time.sleep_ms(1000)
        draw_face(EXPR_HAPPY, 0, 0, 1.0)
        time.sleep_ms(300)
        talk_msg = "Te peguei! >_<"
    elif g == 3:
        for a in range(12):
            draw_face(EXPR_NORMAL, int(3 * math.cos(a * 0.5)), int(3 * math.sin(a * 0.5)), 1.0)
            time.sleep_ms(120)
        talk_msg = "Tontura! @_@"
    elif g == 4:
        draw_face(EXPR_LOVE, 0, 0, 1.0)
        if CFG["neo_efeitos"]:
            neo_pattern(HEART, (255, 30, 100))
        play_melody(M_LOVE)
        time.sleep_ms(1500)
        talk_msg = "Te amo! <3 <3"
    talk_mode = 0
    pet_state = "talking"
    react_end = time.ticks_ms() + 2000
    if CFG["neo_efeitos"] and g != 4:
        neo_clear()

gc.collect()

# ============================================================
# SECTION 10: GAMES
# ============================================================
def game_snake():
    sx = [2]
    sy = [2]
    dx, dy = -1, 0
    score = 0
    speed = 550
    nd = None
    # Spawn food not on snake
    while True:
        fx = random.randint(0, 4)
        fy = random.randint(0, 4)
        ok = True
        for i in range(len(sx)):
            if sx[i] == fx and sy[i] == fy:
                ok = False
                break
        if ok:
            break
    # Countdown
    for c in ("3", "2", "1", "GO!"):
        neo_clear()
        for i in range(len(sx)):
            np[neo_xy(sx[i], sy[i])] = _sc(0, 255, 0)
        np[neo_xy(fx, fy)] = _sc(255, 0, 0)
        np.write()
        oled.fill(0)
        oled.text("SNAKE", 40, 5, 1)
        oled.text(c, 56, 30, 1)
        oled.show()
        beep(800 if c != "GO!" else 1200, 80)
        time.sleep_ms(600)
    last_move = time.ticks_ms()
    while True:
        jx, jy = read_joy()
        if abs(jx) > 35 or abs(jy) > 35:
            if abs(jx) > abs(jy):
                d = "right" if jx > 0 else "left"
            else:
                d = "down" if jy > 0 else "up"
            if d == "up" and dy != -1:
                nd = (0, 1)
            elif d == "down" and dy != 1:
                nd = (0, -1)
            elif d == "left" and dx != -1:
                nd = (1, 0)
            elif d == "right" and dx != 1:
                nd = (-1, 0)
        if btn_b.value() == 0:
            return False
        now = time.ticks_ms()
        if time.ticks_diff(now, last_move) < speed:
            time.sleep_ms(20)
            continue
        last_move = now
        if nd:
            dx, dy = nd
            nd = None
        nx = (sx[0] + dx) % 5
        ny = (sy[0] + dy) % 5
        # Check collision BEFORE moving
        hit = False
        for i in range(len(sx)):
            if sx[i] == nx and sy[i] == ny:
                hit = True
                break
        if hit:
            for f in range(4):
                neo_fill((255, 0, 0) if f % 2 else (0, 0, 0))
                time.sleep_ms(150)
            neo_clear()
            oled.fill(0)
            oled.text("Game Over!", 25, 10, 1)
            oled.text("Score: %d" % score, 35, 30, 1)
            oled.show()
            beep(300, 300)
            time.sleep_ms(2000)
            return False
        sx.insert(0, nx)
        sy.insert(0, ny)
        if nx == fx and ny == fy:
            score += 1
            beep(659, 30)
            if len(sx) > 4:
                sx.pop()
                sy.pop()
            # Spawn new food
            while True:
                fx = random.randint(0, 4)
                fy = random.randint(0, 4)
                ok = True
                for i in range(len(sx)):
                    if sx[i] == fx and sy[i] == fy:
                        ok = False
                        break
                if ok:
                    break
            speed = max(300, speed - 15)
        else:
            sx.pop()
            sy.pop()
        # Render
        for i in range(25):
            np[i] = (0, 0, 0)
        blink = (time.ticks_ms() // 200) % 2
        if blink:
            np[neo_xy(fx, fy)] = _sc(255, 0, 0)
        for i in range(len(sx)):
            brightness = max(50, 255 - i * 30)
            np[neo_xy(sx[i], sy[i])] = _sc(0, brightness, 0)
        np[neo_xy(sx[0], sy[0])] = _sc(50, 255, 50)
        np.write()
        oled.fill(0)
        oled.text("SNAKE", 40, 5, 1)
        oled.text("Score: %d" % score, 35, 25, 1)
        oled.text("B=Sair", 40, 55, 1)
        oled.show()
        if score > 0 and score % 3 == 0:
            gc.collect()

def game_reaction():
    best = 9999
    total = 0
    for r in range(5):
        oled.fill(0)
        oled.text("REACAO!", 35, 5, 1)
        oled.text("Round %d/5" % (r + 1), 25, 25, 1)
        oled.text("Espere...", 30, 42, 1)
        oled.show()
        neo_clear()
        # Wait random time
        wait = 1000 + random.randint(0, 3000)
        t0 = time.ticks_ms()
        early = False
        while time.ticks_diff(time.ticks_ms(), t0) < wait:
            if btn_a.value() == 0:
                early = True
                break
            if btn_b.value() == 0:
                return False
            time.sleep_ms(10)
        if early:
            # Pressed too early = penalty
            neo_fill((255, 0, 0))
            oled.fill(0)
            oled.text("CEDO DEMAIS!", 20, 25, 1)
            oled.show()
            beep(300, 300)
            total += 2000
            time.sleep_ms(1000)
            neo_clear()
            continue
        # GO!
        neo_fill((0, 255, 0))
        beep(880, 30)
        t0 = time.ticks_ms()
        while btn_a.value() == 1:
            if time.ticks_diff(time.ticks_ms(), t0) > 2000:
                break
            if btn_b.value() == 0:
                return False
            time.sleep_ms(5)
        ms = time.ticks_diff(time.ticks_ms(), t0)
        total += ms
        if ms < best:
            best = ms
        oled.fill(0)
        oled.text("Round %d/5" % (r + 1), 25, 5, 1)
        oled.text("%d ms" % ms, 45, 30, 1)
        oled.show()
        neo_clear()
        time.sleep_ms(800)
    oled.fill(0)
    oled.text("RESULTADO", 30, 5, 1)
    oled.hline(0, 14, 128, 1)
    oled.text("Melhor: %dms" % best, 15, 25, 1)
    oled.text("Media: %dms" % (total // 5), 15, 40, 1)
    oled.show()
    time.sleep_ms(3000)
    return best < 350

gc.collect()

# ============================================================
# SECTION 11: UI SCREENS
# ============================================================
MENU = ("Alimentar", "Carinho", "Brincar", "Exercicio", "Snake",
        "Reacao", "Jukebox", "Humor", "Skin", "Status", "Achar Me!", "Config", "Dormir")

def show_menu(sel):
    oled.fill(0)
    oled.text("= MENU =", 30, 0, 1)
    oled.hline(0, 9, 128, 1)
    st = max(0, min(sel - 1, len(MENU) - 4))
    for i in range(min(4, len(MENU) - st)):
        idx = st + i
        y = 13 + i * 11
        if idx == sel:
            oled.fill_rect(0, y - 1, 128, 10, 1)
            oled.text("> " + MENU[idx], 2, y, 0)
        else:
            oled.text("  " + MENU[idx], 2, y, 1)
    oled.text("B=OK A/Joy=Sair", 0, 56, 1)
    oled.show()

def _status_pg(pg):
    age = get_age()
    mins = stats["m"]
    dias = mins // 1440
    hrs = (mins % 1440) // 60
    per = get_personality()
    oled.fill(0)
    if pg == 0:
        draw_clock(1, 1)
        oled.text("EMOCOES", 40, 0, 1)
        oled.hline(0, 9, 128, 1)
        for i, (lbl, key) in enumerate((("F", "happy"), ("H", "hunger"),
                                         ("E", "energy"), ("D", "fun"))):
            y = 11 + i * 9
            v = emotions[key]
            oled.text(lbl, 0, y, 1)
            oled.rect(10, y, 100, 7, 1)
            oled.fill_rect(11, y + 1, v * 98 // 100, 5, 1)
            oled.text("%d" % v, 112, y, 1)
    elif pg == 1:
        oled.text("PERFIL", 40, 0, 1)
        oled.hline(0, 9, 128, 1)
        oled.text(AGE_NAMES[age], 0, 12, 1)
        oled.text("%dd%dh" % (dias, hrs), 72, 12, 1)
        oled.text(per[:12], 0, 23, 1)
        oled.hline(0, 32, 128, 1)
        oled.text("Comeu", 0, 35, 1)
        oled.text(str(stats["f"]), 52, 35, 1)
        oled.text("Jogou", 0, 45, 1)
        oled.text(str(stats["g"]), 52, 45, 1)
    elif pg == 2:
        oled.text("SISTEMA", 36, 0, 1)
        oled.hline(0, 9, 128, 1)
        oled.text("Wi", 0, 12, 1)
        oled.text("OK" if wifi_ok else "--", 24, 12, 1)
        if tem_relogio:
            t = time.localtime()
            ep = time.mktime(t) + CFG["tz"] * 3600
            lt = time.localtime(ep)
            oled.text("%02d:%02d" % (lt[3], lt[4]), 56, 12, 1)
            oled.text("%02d/%02d" % (lt[2], lt[1]), 96, 12, 1)
        gc.collect()
        oled.text("RAM %dKB" % (gc.mem_free() // 1024), 0, 23, 1)
        oled.text("Int %d" % stats["i"], 0, 33, 1)
    oled.hline(0, 55, 128, 1)
    draw_clock(1, 57)
    oled.text("%d/3" % (pg + 1), 52, 57, 1)
    oled.text("< >", 88, 57, 1)
    oled.show()

def show_status():
    pg = 0
    _status_pg(pg)
    beep(800, 20)
    time.sleep_ms(300)
    while True:
        d = get_joy_dir(*read_joy())
        if d == "right":
            pg = (pg + 1) % 3
            _status_pg(pg)
            beep(800, 15)
            time.sleep_ms(200)
        elif d == "left":
            pg = (pg - 1) % 3
            _status_pg(pg)
            beep(800, 15)
            time.sleep_ms(200)
        if btn_a.value() == 0 or btn_b.value() == 0 or btn_joy.value() == 0:
            beep(600, 20)
            time.sleep_ms(200)
            return
        time.sleep_ms(30)

CFG_ITEMS = (
    ("Som", "som", ("Sim", "Nao")),
    ("Volume", "vol", ("Baixo", "Medio", "Alto")),
    ("Noturno", "noturno", ("auto", "liga", "desli")),
    ("Dormir", "hr_dormir", None),
    ("Acordar", "hr_acordar", None),
    ("LED5x5", "brilho", ("Baixo", "Medio", "Alto")),
    ("Mic", "mic_reage", ("Sim", "Nao")),
    ("Efeitos", "neo_efeitos", ("Sim", "Nao")),
    ("Fuso", "tz", None),
)

def show_config():
    global _bs
    sel = 0
    while True:
        oled.fill(0)
        if tem_relogio:
            draw_clock(1, 2)
            oled.text("CONFIG", 45, 0, 1)
        else:
            oled.text("= CONFIG =", 25, 0, 1)
        oled.hline(0, 9, 128, 1)
        st = max(0, min(sel - 1, len(CFG_ITEMS) - 4))
        for i in range(min(4, len(CFG_ITEMS) - st)):
            idx = st + i
            y = 13 + i * 12
            name, key, opts = CFG_ITEMS[idx]
            val = CFG[key]
            if isinstance(val, bool):
                vt = "Sim" if val else "Nao"
            elif key in ("hr_dormir", "hr_acordar"):
                vt = "%dh" % val
            elif key == "tz":
                vt = "UTC%+d" % val
            elif key in ("brilho", "vol"):
                vt = ("Baixo", "Medio", "Alto")[val]
            else:
                vt = str(val)
            txt = "%s:%s" % (name, vt)
            if idx == sel:
                oled.fill_rect(0, y - 1, 128, 11, 1)
                oled.text((">" + txt)[:15], 2, y, 0)
            else:
                oled.text((" " + txt)[:15], 2, y, 1)
        oled.text("B=Muda A=Volta", 5, 55, 1)
        oled.show()
        while True:
            d = get_joy_dir(*read_joy())
            if d == "up":
                sel = (sel - 1) % len(CFG_ITEMS)
                beep(800, 20)
                time.sleep_ms(120)
                break
            if d == "down":
                sel = (sel + 1) % len(CFG_ITEMS)
                beep(800, 20)
                time.sleep_ms(120)
                break
            if btn_b.value() == 0:
                beep(800, 20)
                name, key, opts = CFG_ITEMS[sel]
                if key == "som":
                    CFG["som"] = not CFG["som"]
                elif key == "mic_reage":
                    CFG["mic_reage"] = not CFG["mic_reage"]
                elif key == "neo_efeitos":
                    CFG["neo_efeitos"] = not CFG["neo_efeitos"]
                elif key in ("brilho", "vol"):
                    CFG[key] = (CFG[key] + 1) % 3
                    if key == "brilho":
                        _bs = BRILHO[CFG["brilho"]]
                elif key in ("hr_dormir", "hr_acordar"):
                    CFG[key] = (CFG[key] + 1) % 24
                elif key == "tz":
                    CFG["tz"] = CFG["tz"] + 1 if CFG["tz"] < 14 else -12
                elif key == "noturno":
                    ci = NOT_MODES.index(CFG["noturno"])
                    CFG["noturno"] = NOT_MODES[(ci + 1) % 3]
                save_state()
                time.sleep_ms(200)
                break
            if btn_a.value() == 0:
                beep(600, 20)
                save_state()
                return
            time.sleep_ms(30)

def jukebox():
    sel = 0
    while True:
        oled.fill(0)
        oled.text("= JUKEBOX =", 20, 0, 1)
        oled.hline(0, 9, 128, 1)
        st = max(0, min(sel - 1, len(MUSIC_LIST) - 4))
        for i in range(min(4, len(MUSIC_LIST) - st)):
            idx = st + i
            y = 13 + i * 12
            if idx == sel:
                oled.fill_rect(0, y - 1, 128, 11, 1)
                oled.text("> " + MUSIC_LIST[idx][0], 2, y, 0)
            else:
                oled.text("  " + MUSIC_LIST[idx][0], 2, y, 1)
        oled.text("B=Play A=Volta", 5, 55, 1)
        oled.show()
        while True:
            d = get_joy_dir(*read_joy())
            if d == "up":
                sel = (sel - 1) % len(MUSIC_LIST)
                beep(800, 20)
                time.sleep_ms(120)
                break
            if d == "down":
                sel = (sel + 1) % len(MUSIC_LIST)
                beep(800, 20)
                time.sleep_ms(120)
                break
            if btn_b.value() == 0:
                beep(800, 20)
                play_music(sel)
                time.sleep_ms(300)
                break
            if btn_a.value() == 0:
                return
            time.sleep_ms(30)

HUMORES = ("Alegre", "Serio", "Timido", "Agitado", "Aleatorio")

def set_humor():
    sel = CFG["humor"]
    while True:
        oled.fill(0)
        oled.text("= HUMOR =", 25, 0, 1)
        oled.hline(0, 9, 128, 1)
        for i in range(len(HUMORES)):
            y = 13 + i * 10
            mark = "*" if i == CFG["humor"] else " "
            if i == sel:
                oled.fill_rect(0, y - 1, 128, 10, 1)
                oled.text(">" + mark + HUMORES[i], 2, y, 0)
            else:
                oled.text(" " + mark + HUMORES[i], 2, y, 1)
        oled.text("B=OK A=Volta", 10, 56, 1)
        oled.show()
        while True:
            d = get_joy_dir(*read_joy())
            if d == "up":
                sel = (sel - 1) % len(HUMORES)
                beep(800, 15)
                time.sleep_ms(120)
                break
            if d == "down":
                sel = (sel + 1) % len(HUMORES)
                beep(800, 15)
                time.sleep_ms(120)
                break
            if btn_b.value() == 0:
                beep(1000, 20)
                CFG["humor"] = sel
                actual = sel
                if sel == 4:
                    actual = random.randint(0, 3)
                if actual == 0:
                    emotions["happy"] = 90
                    emotions["fun"] = 80
                elif actual == 1:
                    emotions["happy"] = 50
                    emotions["fun"] = 30
                elif actual == 2:
                    emotions["happy"] = 40
                    emotions["energy"] = 40
                elif actual == 3:
                    emotions["happy"] = 70
                    emotions["fun"] = 95
                    emotions["energy"] = 85
                save_state()
                draw_face_msg(get_expression(), HUMORES[sel] + "!", 0, 0, 1.0)
                time.sleep_ms(1500)
                return
            if btn_a.value() == 0:
                beep(600, 15)
                return
            time.sleep_ms(30)

SKIN_N = ("Classico", "Kawaii", "Robo", "Gato")

def set_skin():
    sel = CFG["skin"]
    old = sel
    while True:
        CFG["skin"] = sel
        draw_face(EXPR_HAPPY, 0, 0, 1.0)
        oled.fill_rect(0, 0, 128, 11, 0)
        oled.text("< " + SKIN_N[sel] + " >", max(0, 64 - (len(SKIN_N[sel]) + 4) * 4), 1, 1)
        oled.hline(0, 10, 128, 1)
        oled.fill_rect(0, 55, 128, 9, 0)
        oled.text("B=OK A=Volta", 15, 56, 1)
        oled.show()
        while True:
            d = get_joy_dir(*read_joy())
            if d == "right" or d == "down":
                sel = (sel + 1) % 4
                beep(800, 15)
                time.sleep_ms(150)
                break
            if d == "left" or d == "up":
                sel = (sel - 1) % 4
                beep(800, 15)
                time.sleep_ms(150)
                break
            if btn_b.value() == 0:
                beep(1000, 20)
                CFG["skin"] = sel
                save_state()
                return
            if btn_a.value() == 0:
                beep(600, 15)
                CFG["skin"] = old
                return
            time.sleep_ms(30)

def find_me():
    nb = BRILHO[CFG["brilho"]]
    for i in range(16):
        if CFG["som"]:
            buzzer.freq(2000 if i % 2 else 1500)
            buzzer.duty_u16(VOL[CFG["vol"]])
        neo_fill((255, 0, 0) if i % 2 else (255, 255, 255))
        oled.fill(0)
        oled.text("AQUI! AQUI!", 20, 10, 1)
        oled.text("ME ACHARAM!", 20, 30, 1)
        oled.text(">>> MOCHI <<<", 15, 50, 1)
        oled.show()
        time.sleep_ms(250)
    buzzer.duty_u16(0)
    neo_clear()
    rgb_off()

gc.collect()

# ============================================================
# SECTION 12: BOOT + MAIN LOOP
# ============================================================
def boot():
    for i in range(25):
        np[i] = _sc(0, 100, 255)
        np.write()
        time.sleep_ms(20)
    oled.fill(0)
    oled.text("MochiPet v2.0", 15, 5, 1)
    oled.text("BitDogLab v6.3", 10, 20, 1)
    oled.hline(5, 32, 118, 1)
    txt = "%s %s" % (AGE_NAMES[get_age()], get_personality())
    oled.text(txt[:15], 5, 37, 1)
    oled.text("A=Come +B=Menu", 5, 49, 1)
    oled.show()
    play_melody(M_WAKE)
    time.sleep_ms(2000)
    neo_clear()

boot()
gc.collect()

# WiFi + NTP
oled.fill(0)
oled.text("Conectando...", 15, 10, 1)
oled.show()
try:
    wifi_connect()
except:
    pass
gc.collect()

if wifi_ok:
    oled.fill(0)
    oled.text("WiFi: OK", 5, 5, 1)
    oled.text("Sincronizando...", 5, 20, 1)
    oled.show()
    ntp_sync()
else:
    oled.fill(0)
    oled.text("WiFi: FALHOU", 5, 5, 1)
    oled.text("Modo offline", 5, 20, 1)
    oled.show()

# Calculate off-time and set base minutes
_session_start = time.ticks_ms()
_base_mins = stats["m"]
if tem_relogio and stats["ep"] > 0:
    _cur_ep = time.mktime(time.localtime()) + CFG["tz"] * 3600
    _off_mins = max(0, (_cur_ep - stats["ep"]) // 60)
    _base_mins += _off_mins
    stats["m"] = _base_mins
    print("Off-time: %d min, total: %d min" % (_off_mins, _base_mins))
save_state()

oled.fill(0)
oled.text("WiFi:%s" % ("OK" if wifi_ok else "OFF"), 0, 5, 1)
oled.text("NTP:%s" % ("%02d:%02d" % (hora_atual, minuto_atual) if tem_relogio else "Sem"), 0, 17, 1)
oled.text("Not:%s" % CFG["noturno"][:5], 0, 29, 1)
oled.text("D:%dh A:%dh" % (CFG["hr_dormir"], CFG["hr_acordar"]), 0, 41, 1)
oled.text("Noite:%s" % ("Sim" if is_noite() else "Nao"), 0, 53, 1)
oled.show()
time.sleep_ms(3000)
gc.collect()

last_interact = time.ticks_ms()
last_decay = time.ticks_ms()
menu_sel = 0
frame = 0
last_neo = time.ticks_ms()
last_clock = time.ticks_ms()
mic_cd = 0
last_wifi_retry = time.ticks_ms() - 270000
last_ntp_retry = time.ticks_ms()
last_ntp_resync = time.ticks_ms()
last_emo_save = time.ticks_ms()
err_count = 0
cur_expr = EXPR_NORMAL
print("RAM livre: %d bytes" % gc.mem_free())

# ---- MAIN LOOP ----
while True:
    try:
        now = time.ticks_ms()
        frame += 1

        # Input edge detection
        a_val = btn_a.value()
        b_val = btn_b.value()
        j_val = btn_joy.value()
        a_pr = a_val == 0 and prev_a == 1
        b_pr = b_val == 0 and prev_b == 1
        j_pr = j_val == 0 and prev_j == 1
        prev_a = a_val
        prev_b = b_val
        prev_j = j_val
        jx, jy = read_joy()
        jdir = get_joy_dir(jx, jy)

        # Clock update every 30s
        if time.ticks_diff(now, last_clock) >= 30000:
            last_clock = now
            update_clock()

        # NTP resync every hour
        if tem_relogio and time.ticks_diff(now, last_ntp_resync) >= 3600000:
            last_ntp_resync = now
            if wifi_ok:
                try:
                    ntp_sync()
                except:
                    pass

        # ---- MENU STATE ----
        if pet_state == "menu":
            if a_pr or j_pr:
                pet_state = "idle"
                beep(600, 20)
                while btn_a.value() == 0 or btn_joy.value() == 0:
                    time.sleep_ms(10)
                time.sleep_ms(100)
            elif jdir == "up":
                menu_sel = (menu_sel - 1) % len(MENU)
                show_menu(menu_sel)
                beep(800, 20)
                time.sleep_ms(120)
            elif jdir == "down":
                menu_sel = (menu_sel + 1) % len(MENU)
                show_menu(menu_sel)
                beep(800, 20)
                time.sleep_ms(120)
            elif b_pr:
                pet_state = "idle"
                beep(1000, 20)
                while btn_b.value() == 0:
                    time.sleep_ms(10)
                time.sleep_ms(100)
                if menu_sel == 0:
                    do_feed()
                elif menu_sel == 1:
                    do_pet()
                elif menu_sel == 2:
                    do_play()
                elif menu_sel == 3:
                    do_exercise()
                elif menu_sel == 4:
                    pet_state = "game"
                    play_melody(M_GS)
                    w = game_snake()
                    if w:
                        play_melody(M_GW)
                        emotions["fun"] = clamp(emotions["fun"] + 30)
                    else:
                        play_melody(M_GL)
                    stats["g"] += 1
                    last_game_time = time.ticks_ms()
                    pet_state = "idle"
                    neo_clear()
                elif menu_sel == 5:
                    pet_state = "game"
                    play_melody(M_GS)
                    w = game_reaction()
                    if w:
                        play_melody(M_GW)
                        emotions["fun"] = clamp(emotions["fun"] + 25)
                    else:
                        play_melody(M_GL)
                    stats["g"] += 1
                    last_game_time = time.ticks_ms()
                    pet_state = "idle"
                elif menu_sel == 6:
                    pet_state = "jukebox"
                    jukebox()
                    pet_state = "idle"
                elif menu_sel == 7:
                    set_humor()
                    talk_msg = ("Yay! ^_^", "Hmph.", "...*olha*", "WHOO!", "~mudando~")[CFG["humor"]]
                    talk_mode = 0
                    pet_state = "talking"
                    react_end = time.ticks_ms() + 3000
                elif menu_sel == 8:
                    set_skin()
                elif menu_sel == 9:
                    show_status()
                elif menu_sel == 10:
                    find_me()
                elif menu_sel == 11:
                    show_config()
                elif menu_sel == 12:
                    draw_face_msg(EXPR_SLEEPY, "Boa noite..", 0, 0, 1.0)
                    play_melody(M_SLEEP)
                    for b in (0.8, 0.5, 0.2):
                        draw_face(EXPR_SLEEPY, 0, 0, b)
                        time.sleep_ms(300)
                    manual_sleep = True
                    pet_state = "sleeping"
            time.sleep_ms(30)
            continue

        # ---- TIMED STATES ----
        if pet_state == "talking" and time.ticks_diff(now, react_end) >= 0:
            pet_state = "idle"
            neo_clear()
        elif pet_state == "reacting" and time.ticks_diff(now, react_end) >= 0:
            pet_state = "idle"
            neo_clear()
        elif pet_state == "eating" and time.ticks_diff(now, react_end) >= 0:
            pet_state = "idle"
            neo_clear()
        elif pet_state == "drowsy":
            if a_pr or b_pr or j_pr:
                do_wake(True)
            elif time.ticks_diff(now, react_end) >= 0:
                pet_state = "sleeping"
        elif pet_state == "sleeping":
            if a_pr or b_pr or j_pr:
                do_wake(True)

        # ---- IDLE/TALKING/REACTING INPUT ----
        # A=Comer, A 2x=Brincar, B tap=Status
        # B segura=Menu, A+B=Achar, Joy btn=Carinho
        if pet_state in ("idle", "reacting", "talking"):
            if btn_a.value() == 0 and btn_b.value() == 0:
                time.sleep_ms(100)
                if btn_a.value() == 0 and btn_b.value() == 0:
                    find_me()
                    time.sleep_ms(300)
                    continue
            if b_pr:
                t0 = time.ticks_ms()
                while btn_b.value() == 0 and time.ticks_diff(time.ticks_ms(), t0) < 800:
                    time.sleep_ms(20)
                if time.ticks_diff(time.ticks_ms(), t0) >= 800:
                    beep(1000, 30)
                    pet_state = "menu"
                    menu_sel = 0
                    show_menu(menu_sel)
                else:
                    show_status()
                continue
            if a_pr:
                if time.ticks_diff(now, last_a_tap) < 400:
                    do_play()
                    last_a_tap = 0
                else:
                    last_a_tap = now
                    do_feed()
            if j_pr:
                do_pet()
            look_x = jx // 25
            look_y = jy // 25

        # ---- MIC REACTION ----
        if CFG["mic_reage"] and time.ticks_diff(now, mic_cd) >= 0 and pet_state in ("idle", "sleeping", "drowsy"):
            lvl = read_mic()
            if lvl > 8000:
                mic_cd = now + 5000
                if pet_state in ("sleeping", "drowsy"):
                    talk_msg = random.choice(FALAS_SONO)
                    talk_mode = 0
                    if pet_state == "sleeping":
                        pet_state = "drowsy"
                    react_end = now + 15000
                    last_interact = now
                elif not is_noite():
                    if lvl > 15000:
                        cur_expr = EXPR_SAD
                        beep(300, 100)
                        talk_msg = random.choice(("PARA!", "Barulheira!", "AI! Para!"))
                        talk_mode = 0
                        pet_state = "talking"
                        react_end = now + 2500
                        if CFG["neo_efeitos"]:
                            neo_fill((255, 0, 0))
                    else:
                        cur_expr = EXPR_SURPRISED
                        beep(800, 30)
                        talk_msg = random.choice(("Hm? Que foi?", "Ouviu isso?", "Que barulho?"))
                        talk_mode = 0
                        pet_state = "talking"
                        react_end = now + 1500

        # ---- EMOTION DECAY ----
        decay_emotions()

        # ---- NIGHT MODE AUTO ----
        if is_noite() and pet_state == "idle" and time.ticks_diff(now, last_interact) > 30000:
            draw_face_msg(EXPR_SLEEPY, "Boa noite..", 0, 0, 1.0)
            play_melody(M_SLEEP)
            for b in (0.8, 0.5, 0.2):
                draw_face(EXPR_SLEEPY, 0, 0, b)
                time.sleep_ms(300)
            pet_state = "sleeping"
        elif not is_noite() and not manual_sleep and pet_state in ("sleeping", "drowsy"):
            wake_count = 0
            oled.contrast(255)
            sleep_mode_active = False
            for b in (0.1, 0.5, 1.0):
                draw_face(EXPR_SLEEPY if b < 0.5 else EXPR_HAPPY, 0, 0, b)
                time.sleep_ms(200)
            play_melody(M_WAKE)
            pet_state = "idle"
            draw_text_only("BOM DIA!", ("Acordei! ^_^", "", AGE_NAMES[get_age()]))
            talk_mode = 1
            pet_state = "talking"
            react_end = now + 4000

        # ---- RANDOM TALK + GRACINHA ----
        maybe_talk()
        if pet_state == "idle" and time.ticks_diff(now, last_gracinha) >= next_gracinha and not is_noite():
            do_gracinha()

        # ---- BLINK ----
        bp = 1.0
        if time.ticks_diff(now, blink_timer) >= 0 and not is_blinking:
            is_blinking = True
            blink_start = now
        if is_blinking:
            el = time.ticks_diff(now, blink_start)
            if el < 70:
                bp = 0.5
            elif el < 120:
                bp = 0.05
            elif el < 170:
                bp = 0.5
            else:
                is_blinking = False
                blink_timer = now + random.randint(3000, 7000)

        # ---- TONGUE (GATO) ----
        if CFG["skin"] == 3 and pet_state in ("idle", "talking", "reacting"):
            if not tongue_out and time.ticks_diff(now, tongue_timer) >= 0:
                tongue_out = True
                tongue_start = now
            if tongue_out and time.ticks_diff(now, tongue_start) > 2000:
                tongue_out = False
                tongue_timer = now + random.randint(15000, 45000)
        elif tongue_out:
            tongue_out = False

        # ---- SLEEP MODE DISPLAY ----
        if pet_state in ("sleeping", "drowsy"):
            if not sleep_mode_active:
                oled.contrast(30)
                neo_clear()
                sleep_mode_active = True
            rgb_off()
        elif sleep_mode_active:
            oled.contrast(255)
            sleep_mode_active = False

        # ---- FACE RENDERING ----
        if pet_state not in ("menu", "game", "jukebox"):
            expr = get_expression()
            if pet_state == "reacting":
                expr = cur_expr
            if pet_state == "drowsy":
                if talk_msg and time.ticks_diff(now, react_end) < -11500:
                    draw_face_msg(EXPR_SLEEPY, talk_msg, 0, 0, bp)
                else:
                    sx = 0
                    sy = 0
                    if time.ticks_diff(now, drowsy_stir) < 0:
                        sx = int(math.sin(now / 333.0) * 1.5)
                        sy = int(math.cos(now / 500.0))
                    elif random.random() < 0.002:
                        drowsy_stir = now + random.randint(1000, 2500)
                    draw_face(EXPR_SLEEPY, sx, sy, bp)
            elif pet_state == "sleeping":
                sx = 0
                sy = 0
                if time.ticks_diff(now, drowsy_stir) < 0:
                    sx = int(math.sin(now / 666.0))
                    sy = int(math.cos(now / 1000.0))
                elif random.random() < 0.001:
                    drowsy_stir = now + random.randint(800, 1500)
                if dream_msg and time.ticks_diff(now, last_dream) < 4000:
                    draw_face_msg(EXPR_SLEEPY, "Zzz " + dream_msg, 0, 0, bp)
                else:
                    if dream_msg:
                        dream_msg = ""
                    if time.ticks_diff(now, next_dream) >= 0:
                        last_dream = now
                        next_dream = now + random.randint(45000, 90000)
                        dream_msg = random.choice(DREAMS)
                    draw_face(EXPR_SLEEPY, sx, sy, bp)
            elif pet_state == "talking" and talk_mode == 0 and talk_msg:
                draw_face_msg(expr, talk_msg, look_x, look_y, bp)
            elif pet_state == "talking" and talk_mode == 1:
                pass
            else:
                draw_face(expr, look_x, look_y, bp)

        # ---- RGB LED STATUS ----
        if pet_state in ("sleeping", "drowsy") or is_noite() or emotions["energy"] < 20:
            rgb_off()
        elif pet_state != "game":
            update_need_led()

        # ---- NEOPIXEL EFFECTS ----
        if CFG["neo_efeitos"] and pet_state == "idle" and not is_noite():
            if time.ticks_diff(now, last_neo) >= 200:
                last_neo = now
                pulse = (now // 100) % 200
                if pulse < 15:
                    h = emotions["happy"]
                    c = (0,150,50) if h > 60 else (150,150,0) if h > 30 else (0,0,150)
                    neo_breathe(c, now / 500.0)
                elif pulse == 15:
                    neo_clear()

        # ---- WIFI + NTP RETRY ----
        if not wifi_ok and time.ticks_diff(now, last_wifi_retry) >= 30000:
            last_wifi_retry = now
            try:
                wifi_connect()
            except:
                pass
            gc.collect()
        if wifi_ok and not tem_relogio and time.ticks_diff(now, last_ntp_retry) >= 15000:
            last_ntp_retry = now
            try:
                ntp_sync()
                if tem_relogio:
                    _cur_ep = time.mktime(time.localtime()) + CFG["tz"] * 3600
                    if stats["ep"] > 0:
                        _off = max(0, (_cur_ep - stats["ep"]) // 60)
                        _base_mins += _off
                        stats["m"] = _base_mins
                    save_state()
            except:
                pass
            gc.collect()

        # ---- AUTO SAVE ----
        if time.ticks_diff(now, last_emo_save) >= 300000:
            last_emo_save = now
            save_state()

        # ---- GC ----
        if frame % 100 == 0:
            gc.collect()
            err_count = max(0, err_count - 1)

        time.sleep_ms(30)

    except MemoryError:
        gc.collect()
        err_count += 1
    except Exception as e:
        err_count += 1
        rgb_off()
        print("ERR:", e)
        if err_count > 20:
            save_state()
            oled.fill(0)
            oled.text("Reiniciando...", 10, 25, 1)
            oled.show()
            time.sleep_ms(1000)
            machine.reset()
        time.sleep_ms(100)
