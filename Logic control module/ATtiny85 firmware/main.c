#include <avr/io.h>

#define F_CPU 8000000L // 8 MHz internal

//avrdude -C USBtiny -p t85 -P USB -U flash:w:"ATtiny85 clock.hex":i
//avrdude -c USBtiny -p t85 -P USB-U efuse:w:0xFF:m -U hfuse:w:0xD7:m -U lfuse:w:0xE2:m

/*
attiny85-8.name=ATtiny85 (internal 8 MHz clock)
attiny85-8.bootloader.low_fuses=0xe2
attiny85-8.bootloader.high_fuses=0xd7
attiny85-8.bootloader.extended_fuses=0xff
attiny85-8.upload.maximum_size=8192
attiny85-8.build.mcu=attiny85
attiny85-8.build.f_cpu=8000000L
attiny85-8.build.core=arduino:arduino
attiny85-8.build.variant=tiny8
*/

#define set_bit(reg,bit) reg|=(1<<bit)
#define clr_bit(reg,bit) reg&=~(1<<bit)
#define tog_bit(reg,bit) reg^=(1<<bit)
#define set_bit_to_value(reg,bit) reg^=((1<<bit))

#define DELAY_LOOP(loop_count) for (long i=0;i<loop_count;i++) { asm("nop");}

#define CLK_PIN 4 // IC pin 3: PB4, Timer 1, OC1B - MUSIC (was speaker)
#define ADC_PIN 3 // IC pin 2: PB3, ADC3

#define PAUSE_THRESHOLD 100
#define MAX_THRESHOLD 1000
#define LOOP_TIMER 200 // main loop timer frequency
#define MIN_FREQ 2
#define MAX_FREQ 1000000

void setup_pins(void)
{
	DDRB = (1 << CLK_PIN); // OUTPUT CLK_PIN		
}

void setup_timer1(void)
{
	// Change music speaker to a hardware pin that Timer1 supports - i.e. pin4 = PB4
	TCCR0A = 0;//notone0A();
	TIMSK = 0;

	TCCR1 = 0 ;
	GTCCR = 0;
	TIFR = 0;
	
	GTCCR = (1 << COM1B0); // set the OC1B to toggle on match
}

void timer1_setfreq(unsigned long frequency)
{
	uint32_t ocr;
	uint8_t prescalarbits = 0b001;
	
	ocr = F_CPU / (2 * frequency);
	
	 prescalarbits = 1;
	 while (ocr > 0xff && prescalarbits < 15) {
		 prescalarbits++;
		 ocr>>=1;
	 }
	 
	 // slowest freq setting is prescalarbits = 15, ocr =255
	 // 15 prescalarbit = 16384
	 // slowest freq = 8 MHz / (16384 * (255+1)) = 1.9 Hz
	
	ocr -= 1;
	
	//TCNT1 = 0; // timer 1 counter = 0	
	TCCR1 = (1<<CTC1)| (prescalarbits<<CS10); // CTC1 : Clear Timer/Counter on Compare Match, after compare match with OCR1C value
	OCR1C = ocr; // set compare value
}


uint16_t readADC(uint8_t adcpin)
{
	uint16_t value=0;
	
	for (uint8_t i=0;i<16;i++)
	{
		ADCSRA &=~(1<<ADEN); // disable ADC Enable, to be safe
		
		//while (ADCSRA & (1<<ADSC)); // wait for ADSC bit to clear
		
		ADMUX = (adcpin & 7) << (MUX0); // REF bits are zero = Vcc as voltage reference
		// ref = 0 : Vcc as voltage reference
		// ref = (1<<REFS1) : 1.1 V internal as reference
		ADCSRA = (1<<ADEN) | (1<<ADPS2) | (1<<ADPS1) | (1<<ADPS0);// divide by 16 | (1<<ADPS1);// | (1<<ADPS0); // Enable ADC in general
		
		ADCSRA |= (1<<ADSC); // Start ADC conversion
		while(ADCSRA & (1<<ADSC)); // ADSC goes to zero when finished
		//while(!(ADCSRA & (1<<ADIF)));
		value+=ADC;
	}
	return value>>4; // divide by eight, average
}

int main(void)
{
	uint16_t looptimer=0,adc_value=0;
	setup_pins();
	setup_timer1();
	
	while (1)
	{
		looptimer++;
		if (looptimer>=LOOP_TIMER) // check in with ADC check every LOOP_TIMER main loop times
		{
			looptimer=0;
			adc_value = readADC(ADC_PIN);
			
			if (adc_value<PAUSE_THRESHOLD)
			{	
				TCCR1 = (1<<CTC1); // prescalar bits = 0 = no timer1
			}
			else if (adc_value>MAX_THRESHOLD)
			{
				timer1_setfreq(MAX_FREQ);
			}
			else
			{
				adc_value -= PAUSE_THRESHOLD;
				uint16_t new_freq;
				
				new_freq = MIN_FREQ + (adc_value>>4); // * 8 
				
				timer1_setfreq(new_freq);
			}
			
		}
	}
}
