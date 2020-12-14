from machine import Pin, PWM, deepsleep
import urequests
import network
import socket
import ujson
#import select
from time import sleep


f = open("config.json", "r")
config_json = f.read()                         #pobranie danych konfiguracyjnych z pliku config.json
config_dict = ujson.loads(config_json)         #zdekodowanie danych json - zamiana na dictionary

f.close()
del config_json

#---------------------------------------   KONFIGURACJA URZĄDZENIA   ---------------------------------------
static_ip = config_dict["static_ip"]
mask_ip = config_dict["mask_ip"]
gate_ip = config_dict["gate_ip"]
dns_ip = config_dict["dns_ip"]
ssid = config_dict["ssid"]
password = config_dict["password"]

server_ip = config_dict["server_ip"]
server_port = config_dict["server_port"]
device_idx = config_dict["device_idx"]

pin_r = Pin(int(config_dict["pin_r"]))          #pobranie numeru pinu z pliku konfiguracyjnego
pin_g = Pin(int(config_dict["pin_g"]))          #pobranie numeru pinu z pliku konfiguracyjnego
pin_b = Pin(int(config_dict["pin_b"]))          #pobranie numeru pinu z pliku konfiguracyjnego

request_period = int(config_dict["request_period"])
pwm_pins_invert = config_dict["pwm_pins_invert"]
#cmd_on = config_dict["cmd_on"]
#cmd_off = config_dict["cmd_off"]

del config_dict
#------------------------------------------------------------------------------------------------------------



#-------------------------------------------   ZMIENNE GLOBALNE   -------------------------------------------
status_rgb = False
color_r = 0
color_g = 0
color_b = 0
#------------------------------------------------------------------------------------------------------------



#------------------------------------------   KONFIGURACJA PINÓW   ------------------------------------------
led = Pin(2, Pin.OUT)    #wbudowana dioda led

led_r = PWM(pin_r, freq=500)
led_g = PWM(pin_g, freq=500)
led_b = PWM(pin_b, freq=500)
#------------------------------------------------------------------------------------------------------------



#-----------------------------------   KONFIGURACJA POŁĄCZEŃ SIECIOWYCH   -----------------------------------
#utworzenie socketu do komunikacji 
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

#inicjalizacja WLAN
wlan = network.WLAN(network.STA_IF)

wlan.active(True)
wlan.ifconfig((static_ip, mask_ip, gate_ip, dns_ip))
wlan.connect(ssid, password)
#------------------------------------------------------------------------------------------------------------



#-----------------------------------------   PODŁĄCZENIE DO SIECI   -----------------------------------------
#oczekiwanie na podłączenie urządzenia Wi-Fi
print("Oczekiwanie na podłączenie do sieci Wi-Fi")

while wlan.isconnected() == False:
    led.value(1)
    sleep(0.2)
    led.value(0)
    sleep(0.2)
    print(".", end =" ")
    
print("")
print("Połączenie udane")
print("Konfigurajca Wi-Fi:  ", end =" ")
print(wlan.ifconfig())

#sygnalizacja podłączenia do sieci - LED
led.value(1)
sleep(2)
led.value(0)
for i in range(5):
    led.value(1)
    sleep(0.1)
    led.value(0)
    sleep(0.1)

#nasłuchiwanie na porcie 80 
s.bind(('', 80))
s.listen(3)
#------------------------------------------------------------------------------------------------------------



#-----------------------------------------------   FUNKCJE   ------------------------------------------------

#funkcja pobierająca i konwertująca dane z serwera domoticz
def get_data_from_domoticz():
    global status_rgb, color_r, color_g, color_b, server_ip, server_port, device_idx
    value = 0     #zmienna używana do ustawienia jasności każdego koloru
    
    response = urequests.get('http://' + server_ip + ':' + server_port + '/json.htm?type=devices&rid=' + device_idx)    #odpowiedź serwera
    #print(response.text)

    parsed_result = ujson.loads(response.text)                                            #konwersja json do dictionary
    #print(parsed_result["result"][0]["Color"])


    colors = ujson.loads(parsed_result["result"][0]["Color"])                             #konwersja json do dictionary - kolory

    status = parsed_result["result"][0]["Status"]                                         #status ("off"  lub  Set Level: xx%)

    #print(status.find("Set Level:"))
    #print(status.find("Off"))
    #print(status)



    if(status.find("Set Level:") == 0):                                       #jeżeli urządzenie włączone
        status_rgb = True                         #ustawienie flagi statusu
        value = int(status.split(" ")[2])         #procentowa wartość jasności
        
    elif(status.find("On") == 0):                                             #jeżeli urządzenie włączone - suwak ustwaiony na 100%
        status_rgb = True                         #ustawienie flagi statusu
        value = 100                               #procentowa wartość jasności

    elif(status.find("Off") == 0):                                            #jeżeli urządzenie wyłączone
        status_rgb = False                        #ustawienie flagi statusu
        value = 0                                 #procentowa wartość jasności
    


    color_r = colors["r"] * value/25               #wartość koloru r
    color_g = colors["g"] * value/25               #wartość koloru g
    color_b = colors["b"] * value/25               #wartość koloru b
    
    print("RGB values: R: " + str(color_r) + "  G: " + str(color_g) + "  B: " + str(color_b))
    
    
    
#funkcja sterująca diodami rgb    
def set_rgb(ststus_rgb, r, g, b):
    global pwm_pins_invert
     
    if(pwm_pins_invert == "False"):                          #jeżeli pwm_pins_invert = 0  ->  nie odwracaj polaryzacji pwm
        r = int(round(r,0))
        g = int(round(g,0))
        b = int(round(b,0))
        r_off = 0
        b_off = 0
        g_off = 0
    elif(pwm_pins_invert == "True"):                         #jeżeli pwm_pins_invert = 1  ->  odwróć polaryzacje pwm
        r = 1023 - int(round(r,0))
        g = 1023 - int(round(g,0))
        b = 1023 - int(round(b,0))
        r_off = 1023
        b_off = 1023
        g_off = 1023
        
       
       
    if(status_rgb == True):                                #rgb włączone
        led_r.duty(r)
        led_g.duty(g)
        led_b.duty(b)
    elif(status_rgb == False):                             #rgb wyłączone
        led_r.duty(r_off)
        led_g.duty(g_off)
        led_b.duty(b_off)

    print("PWM values: R: " + str(r) + "  G: " + str(g) + "  B: " + str(b))
    print("")

#------------------------------------------------------------------------------------------------------------






#----------------------------------------   GŁÓWNA PĘTLA PROGRAMU   -----------------------------------------
while True:
    get_data_from_domoticz()                                #pobranie informacji o stanie urządzenia z serwera domoticz
    set_rgb(status_rgb, color_r, color_g, color_b)          #wysterowanie diod rgb
    sleep(request_period)                                   #opóźnienie 
#------------------------------------------------------------------------------------------------------------    
