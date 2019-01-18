#from periphery import GPIO

# the following are not used!
board_chronos14_ioports = {
    "ddr3-i2c" :       "/dev/i2c-0",
    "eeprom-i2c" :     "/dev/i2c-1",
    "lux1310-spidev" : "/dev/spidev3.0",
    "lux1310-dac-cs" : "/sys/class/gpio/gpio33/value",
    "lux1310-color" :  "/sys/class/gpio/gpio66/value",
    "encoder-a" :      "/sys/class/gpio/gpio20/value",
    "encoder-b" :      "/sys/class/gpio/gpio26/value",
    "encoder-sw" :     "/sys/class/gpio/gpio27/value",
    "shutter-sw" :     "/sys/class/gpio/gpio66/value",
    "record-led.0" :   "/sys/class/gpio/gpio41/value",
    "record-led.1" :   "/sys/class/gpio/gpio25/value",
    "trigger-pin" :    "/sys/class/gpio/gpio127/value",
    "frame-irq" :      "/sys/class/gpio/gpio51/value",
    # FPGA Programming Pins 
    "ecp5-spidev" :    "/dev/spidev3.0",
    "ecp5-progn" :     "/sys/class/gpio/gpio47/value",
    "ecp5-init" :      "/sys/class/gpio/gpio45/value",
    "ecp5-done" :      "/sys/class/gpio/gpio52/value",
    "ecp5-cs" :        "/sys/class/gpio/gpio58/value",
    "ecp5-holdn" :     "/sys/class/gpio/gpio58/value" 
    }
