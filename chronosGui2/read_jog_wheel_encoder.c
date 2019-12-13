//Poll every 0.75ms for encoder knob changes.
//TODO DDR 2018-10-02: This should wait for event like in camApp's userInterface.cpp, but I'm having some difficulty making that work. This polling eats up about 2% CPU it seems, and may keep the CPU in a higher-power state?
//	(eg. `ret = poll(fds, sizeof(fds)/sizeof(struct pollfd), ENC_SW_DEBOUNCE_MSEC);`)
//To build: run `gcc read_jog_wheel_encoder.c -O3 -o read_jog_wheel_encoder` on a camera build env.

#include <fcntl.h>  //usleep
#include <signal.h> //signal
#include <stdio.h>  //fputc
#include <unistd.h> //stdout

char a_old, a_new, b_old, b_new;
unsigned int stop;

void sig_handler(int signo) { stop = 1; }

int main(int argc, char**argv) {
	signal(SIGINT, sig_handler);
	//setvbuf(stdout, NULL, _IONBF, 0);
	
	int jogWheelEncoderA = open("/sys/class/gpio/gpio20/value", O_RDONLY|O_NONBLOCK);
	int jogWheelEncoderB = open("/sys/class/gpio/gpio26/value", O_RDONLY|O_NONBLOCK);
	
	while(!stop) {
		//Delay to avoid eating all CPU. Only eat some. (Could be avoided if DDR could figure out polling. 🙄)
		usleep(750); //ns, 1000 = 1ms. 16ms = 1 frame at 60fps.
		
		//Seek back to the beginning of the encoder FIFOs. They seem to be two bytes long, '0' or '1', followed by '\n'.
		lseek(jogWheelEncoderA, 0, SEEK_SET);
		lseek(jogWheelEncoderB, 0, SEEK_SET);
		read(jogWheelEncoderA, &a_new, sizeof(char));
		read(jogWheelEncoderB, &b_new, sizeof(char));
		
		//We only care about changes. Discard any duplicate readings.
		if(a_new == a_old && b_new == b_old) { continue; }
		a_old = a_new;
		b_old = b_new;
		
		fputc(a_new, stdout);
		fputc(b_new, stdout);
		fputc('\n', stdout);
		fflush(stdout);
	}
	
	return 0;
}