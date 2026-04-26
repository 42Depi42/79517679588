import threading
def led():
    global migalochka
    migalochka= True
    while migalochka:
        leds_array = ([LEDState(i, 255, 0, 0) for i in range(36)])
        set_leds(leds_array)
        rospy.sleep(1)
        leds_array = ([LEDState(i, 0, 0, 0) for i in range(36)])
        set_leds(leds_array)
        leds_array = ([LEDState(i, 0, 0, 255) for i in range(36,72)])
        set_leds(leds_array)
        rospy.sleep(1)
        leds_array = ([LEDState(i, 0, 0, 0) for i in range(36,72)])
        set_leds(leds_array)
def start_led():
    threading.Thread(target=led,daemon=True).start()