#include <avr/io.h>
#include <stdio.h>
#include <avr/pgmspace.h>
#include "control_EEPROM0.h"
#include "control_EEPROM1.h"
#include "control_EEPROM2.h"
#include "signals.h"

#define F_CPU 20000000 // 20 MHz
#define BAUDRATE 19200
#define BAUD_PRESCALLER (((F_CPU / (BAUDRATE * 16UL))) - 1)

//https://www.arduino.cc/reference/tr/language/variables/utilities/progmem/

// ATMega328p control logic sketch

#define set_bit(reg,bit) reg|=(1<<bit)
#define clr_bit(reg,bit) reg&=~(1<<bit)
#define tog_bit(reg,bit) reg^=(1<<bit)
#define set_bit_to_value(reg,bit) reg^=((1<<bit))

// ADC useful definitions

#define SHIFT_DATA_PIN 0	// PB0
#define SHIFT_CLK_PIN 1 	// PB1
#define SHIFT_LATCH_PIN 2	// PB2

#define DATABUS_OUT_PIN 0 //PC0
#define CLK_PIN	1 // PC1
#define DATABUS_READ_PIN 2 // PC2
#define DATABUS_QH_PIN 3 // PC3

#define IGNORE_ADC 1
#define ADC_PIN 7// PORT C Change to 7 on actual board else use PC3 (databus_QH to test)

#define CLK_PAUSE 0
#define CLK_RUNNING 1
#define CLK_MAX 2
#define CLK_HALT 3

#define DELAY_LOOP(loop_count) for (uint32_t i=0;i<loop_count;i++) { asm("nop");}
#define PAUSE_THRESHOLD 50
#define MAX_THRESHOLD 1000
#define LOOP_MINIMUM 100


void USART_init(void){
	UBRR0H = (uint8_t)(BAUD_PRESCALLER>>8);
	UBRR0L = (uint8_t)(BAUD_PRESCALLER);
	UCSR0B = (1<<RXEN0)|(1<<TXEN0);
	UCSR0C = ((1<<UCSZ00)|(1<<UCSZ01));
	//http://www.avrfreaks.net/forum/usart-interrupts-atmega328p-solved
	
	//UCSR0B |= (1<<RXCIE0); // Enable RX interrupt.
	
	//UART_buffer.read_pos=0;
	//UART_buffer.write_pos=0;
}

uint8_t USART_ready(void)
{
	return (UCSR0A & (1<<RXC0));
}
void USART_send(uint8_t data){	
	while(!(UCSR0A & (1<<UDRE0)));
	UDR0 = data;
}

unsigned char USART_receive(void){
	while(!(UCSR0A & (1<<RXC0))); //loops forever until byte recieved
	return UDR0;
}

void USART_putstring(char* StringPtr)
{
	while(*StringPtr != 0x00){
		USART_send(*StringPtr);
		StringPtr++;
	}
}

void print_bin8(uint8_t number, uint8_t zero_b, uint8_t carriage)
{
	if (zero_b)
	{
		USART_send('0');
		USART_send('b');
	}
	
	for (int8_t i=7; i>=0;i--)
	{
		uint8_t bit = (number>>i)&1;
		USART_send('0'+bit);
	}
	if (carriage)
	{
		USART_send(10);
		USART_send(13);
	}
}

void print_bin16(uint16_t number, uint8_t zero_b, uint8_t carriage)
{
	uint8_t high = number>>8;
	uint8_t low = number & 0xff;
	print_bin8(high,zero_b,0);
	USART_send('|');
	print_bin8(low,0,carriage);
}


void setup_pins()
{
	// PORTD = I0-I7
	DDRD = 0; // set all PORTD pins to INPUTS

	// PB0 = SHIFT_DATA (output)
	// PB1 = SHIFT_CLK (output)
	// PB2 = SHIFT_LATCH (output)
	//DDRB = 0b00000111; // Set PB0-2 for control signal shifting
	DDRB = (1<<SHIFT_LATCH_PIN) | (1<<SHIFT_CLK_PIN) | (1<<SHIFT_DATA_PIN);
	clr_bit(PORTB,SHIFT_DATA_PIN);
	clr_bit(PORTB,SHIFT_CLK_PIN);
	clr_bit(PORTB,SHIFT_LATCH_PIN);	

	// PC0 = DATABUS_OUT (output)
	// PC1 = CLK (output)
	// PC2 = DATABUS_READ (output)
	// PC3 = DATABUS_QH (input)
	// PC4 = FLAG_C (input)
	// PC5 = FLAG_Z (input)
	
	DDRC = (1<<DATABUS_READ_PIN) | (1<<CLK_PIN) | (1<<DATABUS_OUT_PIN); //0b00000111;
	set_bit(PORTC,DATABUS_OUT_PIN); // PC0, DATABUS_OUT = High (active low)	
	clr_bit(PORTC,CLK_PIN); // PC1, CLK
	set_bit(PORTC,DATABUS_READ_PIN); // PC2, DATABUS_READ = High (active low)

	clr_bit(PORTC,ADC_PIN); // disable pull-up resistor for ADC_PIN
	if (ADC_PIN<=5) DIDR0 |= (1<<ADC_PIN); // ADC6 and ADC7 do not have digital input buffers
	
}

void adc_setup()
{
		// ADC setup:
		//https://www.avrfreaks.net/s/topic/a5C3l000000UVHoEAO/t134058
		ADCSRA &=~(1<<ADEN); // disable ADC Enable, to be safe
		
		ADMUX = (1<<REFS0) | ADC_PIN; // AVCC reference voltage, use ADC7
		//ADMUX = (1<<REFS1) | (1<<REFS0) | ADC_PIN; // 1.1V internal ref
		ADCSRA = (1<<ADEN) | (1<<ADPS2)| (1<<ADPS1) | (1<<ADPS0); //Enable ADC, use pre-scaler = 128 (note pre-scalers lower than 4 gave ADC=1023)
		ADCSRA |= (1<<ADSC) ; //Start the conversion
}


inline void shift_out_byte_595(uint8_t shift_byte)
{
	// Shift register 74HC595 clocks into Qa first then Qb, Qc, etc
	// We need to reverse the bit order in define_instructions.py so that Qa is MSB (i.e. #Ai)
	// rather than LSB
	uint8_t i;
	
	for (i=0;i<8;i++)
	{	
		clr_bit(PORTB,0);	//PB0 = Shift data bit pin
		PORTB |= (shift_byte&1);
		set_bit(PORTB,SHIFT_CLK_PIN);
		shift_byte>>=1;
		clr_bit(PORTB,SHIFT_CLK_PIN); // Clock in serial
	}	
}

uint8_t read_databus(void)
{
	uint8_t read_byte,bit;
	
	clr_bit(PORTC, DATABUS_READ_PIN);
	set_bit(PORTC, DATABUS_READ_PIN);
	
	read_byte = 0;
	for (uint8_t i=0; i<7;i++) // get MSB FIRST Qh
	{ // only do this loop 7 times, then a final read - CHECK datasheet!
		bit = (PINC >> DATABUS_QH_PIN) & 1;
		read_byte |= bit;
		set_bit(PORTB,SHIFT_CLK_PIN);
		read_byte <<= 1; // Shift to left
		clr_bit(PORTB,SHIFT_CLK_PIN);
	}
	bit = (PINC >> DATABUS_QH_PIN) & 1;
	read_byte |=bit; // Final Qh read goes into LSB (started as D0 = A position)
	
	return read_byte;
}

void print_hex_nibble(uint8_t nibble)
{
	uint8_t hexchars[] ={'0','1','2','3','4','5','6','7','8','9','A','B','C','D','E','F'};
	USART_send(hexchars[nibble]);
}

void print_hex8(uint8_t number)
{
	uint8_t hi, low;
	
	USART_send('0');
	USART_send('x');
	
	hi = number>>4;
	low = number & 0x0F;
	
	print_hex_nibble(hi);
	print_hex_nibble(low);
}

void print_hex16(uint16_t number)
{
	
	USART_send('0');
	USART_send('x');

	print_hex_nibble(number>>12);
	print_hex_nibble((number>>8)&0x0F);
	print_hex_nibble((number>>4)&0x0F);
	print_hex_nibble(number&0x0F);
}

int main(void)
{
	uint8_t flags, instruction, microcode_counter=0;
	uint8_t control_byte0, control_byte1, control_byte2;
	uint16_t address; // format = Z | C | m2 | m1 | m0 | I0-I7

	uint16_t clock_ADC; // raw 10-bit ADC value
	char buffer[30];
	uint32_t loop_wait=1000000; // initialise to a slow value, just in case
	uint8_t clock_status = CLK_PAUSE;
	
	setup_pins();
	adc_setup();
	USART_init();
	
    /*shift_out_byte_595(0x01); // just a test
				
	set_bit(PORTB,SHIFT_LATCH_PIN);	// Latch output
	clr_bit(PORTB,SHIFT_LATCH_PIN);
	*/
    while (1) 
    {
		
		if ((ADCSRA & (1<<ADSC))==0) // ADSC bit goes to 0
		{
			#ifdef IGNORE_ADC
				clock_ADC = PAUSE_THRESHOLD; // slowest possible clock
			#else
				clock_ADC = ADC; // 10-bit read
			#endif
			ADCSRA |= (1<<ADSC) ; //Start a conversion
			
			// decide on State based on whether we are paused, running or max running.
			if (clock_ADC<PAUSE_THRESHOLD)
			{
				clock_status = CLK_PAUSE;
				loop_wait=69; // value will be ignored but good to set just in case of a bug
			}
			else if (clock_ADC>MAX_THRESHOLD)
			{
				clock_status = CLK_MAX;
				loop_wait=LOOP_MINIMUM; // We could specify the maximum stable clock
			}
			else
			{
				clock_status = CLK_RUNNING;
				loop_wait = LOOP_MINIMUM + ((MAX_THRESHOLD-(uint32_t) clock_ADC)<<10);
				// clock_ADC = 0, loop_wait = 1023*1024 = 1 Million-ish
				// clock_ADC = 1023, loop_wait = 0;
			}
			/*sprintf(buffer,"%lu\n",loop_wait);
			USART_putstring(buffer);
			USART_send(10);
			USART_send(13);*/
			ADCSRA |= ADSC; //Start a conversion
		}
		
		if (clock_status==CLK_MAX || clock_status==CLK_RUNNING)
		{
			// shift out bytes here
			instruction = PIND; // reads PORTD
			flags = PINC & 0b110000;
			address = flags<<7 | microcode_counter<<8 | instruction;
			//print_bin16(address,1,1);
			
			control_byte0 = pgm_read_byte(control0+address); // Need to think carefully about order signals emerge from shift register
			control_byte1 = pgm_read_byte(control1+address);
			control_byte2 = pgm_read_byte(control2+address);
					
			print_hex16(address);
			USART_send('*');
			print_hex8(instruction);
			USART_send('|');
			print_hex8(microcode_counter);
			USART_send('|');
			print_hex8(flags);		
			USART_send(':');
			print_hex8(control_byte0);
			USART_send(':');
			print_hex8(control_byte1);
			USART_send(':');
			print_hex8(control_byte2);
			
			USART_send(10);
			USART_send(13);
			
			shift_out_byte_595(control_byte2);
			shift_out_byte_595(control_byte1);
			shift_out_byte_595(control_byte0);
			
			set_bit(PORTB,SHIFT_LATCH_PIN);	// Latch output of control signals
			clr_bit(PORTB,SHIFT_LATCH_PIN);
			
			DELAY_LOOP(loop_wait);
			set_bit(PORTC,CLK_PIN);
			microcode_counter++;
			if (control_byte0 & (1<<SIGNAL_MC_reset))
			{
				microcode_counter = 0;
				USART_putstring("MC_RESET");
			}
			microcode_counter&=7; // for now
			DELAY_LOOP(loop_wait);
			clr_bit(PORTC,CLK_PIN);
			ADCSRA |= ADSC ; //Start a conversion again because we changed a pin on port C
		}
		
		if (USART_ready()){
			char uart_byte = USART_receive();
			if (uart_byte=='o')
			{
				clr_bit(PORTC,DATABUS_OUT_PIN);
				DELAY_LOOP(1000000);
				set_bit(PORTC,DATABUS_OUT_PIN);
			}
			if (uart_byte=='r')
			{
				print_bin8(read_databus(),1,1);
			}
			if (uart_byte=='p')
			{
				while(!USART_ready());
				uart_byte = USART_receive();
			}
			shift_out_byte_595(uart_byte);
			set_bit(PORTB,SHIFT_LATCH_PIN);	// Latch output
			clr_bit(PORTB,SHIFT_LATCH_PIN);
			//USART_send(uart_byte);
		}
		
		
    }
}

