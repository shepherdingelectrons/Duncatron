#include <avr/pgmspace.h>
#include "control_EEPROM0.h"
#include "control_EEPROM1.h"
#include "control_EEPROM2.h"

//https://www.arduino.cc/reference/tr/language/variables/utilities/progmem/

// ATMega328p control logic sketch

#define set_bit(reg,bit) reg|=(1<<bit)
#define clr_bit(reg,bit) reg&=!(1<<bit)
#define tog_bit(reg,bit) reg^=(1<<bit)

// ADC useful definitions
#define REFS1 (1<<7)
#define REFS0 (1<<6)

#define ADEN (1<<7) // Enables ADC module
#define ADSC (1<<6)	// Setting to 1 initiates a single ADC read. Changes to 0 when complete

#define SHIFT_DATA_PIN 0	; PB0
#define SHIFT_CLK_PIN 1 	; PB1
#define SHIFT_LATCH_PIN 2	; PB2

void setup_pins()
{
// PORTD = I0-I7
DDRD = 0; // set all PORTD pins to INPUTS

// PB0 = SHIFT_DATA (output)
// PB1 = SHIFT_CLK (output)
// PB2 = SHIFT_LATCH (output)
DDRB = 0b00000111; // Set PB0-2 for control signal shifting
clr_bit(PORTB,0);
clr_bit(PORTB,1);
clr_bit(PORTB,2);

// PC0 = DATABUS_OUT (output)
// PC1 = CLK (output)
// PC2 = DATABUS_READ (output)
// PC3 = DATABUS_QH (input)
// PC4 = FLAG_C (input)
// PC5 = FLAG_Z (input)
DDRC = 0b00000111; 
set_bit(PORTC,0); // PC0, DATABUS_OUT = High (active low)
clr_bit(PORTC,0); // PC1, CLK
set_bit(PORTC,2); // PC2, DATABUS_READ = High (active low)

// ADC setup:
ADMUX = REFS0 | 7; // AVCC reference voltage, use ADC7
ADCSRA = ADEN | 0 ; Enable ADC, use pre-scaler = 2
ADCSRA |= ADSC ; Start the conversion

// https://avr-guide.github.io/timers-on-the-atmega328/
#define WGM00 0
#define WGM01 1
#define CS01 1
#define CS00

TCCR1A |= (1 << WGM11); // Set the Timer Mode to CTC
OCR1A = 0xF9; // Set the value that you want to count to
// start the timer
TCCR1B |= (1 << CS01) | (1 << CS00); // set prescaler to 64 and start the timer
TIMSK1 = 0; // Timer/Counter Interrupt Mask Register, no interupts
//TIFR0 : OCF0B | OCF0A | TOV0
// OCF0B: Compare B Match Flag
// OCF0A: Compare A Match Flag
// TOV0: Timer/Counter0 Overflow flag, is set when an overflow occurs in Timer/Counter0.
//			TOV0 is cleared by hardware when executing the corresponding interrupt handling vector.
//			Alternatively, TOV0 is cleared by writing a logic one to the flag. When the SREG I-bit, 
//			TOIE0 (Timer/Counter0 overflow interupt enable), and TOV0 are set, the Timer/Counter0 overflow
//			interrupt is executed.  The setting of this flag is dependent of the WGM02:0 bit setting.
// TCNT0 - Timer/Counter Register
}

/* Notes:
set_bit(PORTB,3); // sets output 

instruction = PIND; // reads PORTD 
flags = PINC & 0b110000
uint8_t microcode_counter = 0;

uint16_t address; // format = Z | C | m2 | m1 | m0 | I0-I7
address = flags<<7 | microcode_counter<<8 | instruction ;
// As address is uint16_t I assume compiler will cast uint8_t to uint16_t in this expression, but needs to be tested

Or do I want FLASH memory (I think PROGMEM=FLASH)? Not sure, need to refresh myself on memory types
Can I forget PROGMEM and see if it compiles? 

*/

inline void shift_out_byte(shift_byte)
{
	// Shift register 74HC595 clocks into Qa first then Qb, Qc, etc
	// We need to reverse the bit order in define_instructions.py so that Qa is MSB (i.e. #Ai)
	// rather than LSB
	for (uint8_t i=0;i++;i<8)
	{
		PORTB &= (0b11111110 | (shift_byte & 1)); //PB0 = Shift data bit pin
		set_bit(PORTB,SHIFT_CLK_PIN);
		shift_byte>>=1;
		clr_bit(PORTB,SHIFT_CLK_PIN); // Clock in serial
	}
	
}

#define CLK_STOPPED 0
#define CLK_ADC 1
#define CLK_MAX 2

void main()
{
uint8_t flags, instruction, microcode_counter=0;
uint16_t address; // format = Z | C | m2 | m1 | m0 | I0-I7
uint16_t clock_ADC; // raw 10-bit ADC value
uint8_t clock_status = CLK_ADC;

setup_pins();

while(True) // Logic never stops, never sleeps, is always vigilant
{
	if (ADCSRA & ADSC)==0 // ADSC bit goes to 0
	{
		clock_ADC = ADC; // 10-bit read
		ADCSRA |= ADSC ; Start a conversion
	}
	
	if (somekind of timer condition)
	{
		instruction = PIND; // reads PORTD 
		flags = PINC & 0b110000;
		address = flags<<7 | microcode_counter<<8 | instruction;
		
		control_byte0 = pgm_read_byte(control0+address); // Need to think carefully about order signals emerge from shift register
		control_byte1 = pgm_read_byte(control1+address); 
		control_byte2 = pgm_read_byte(control2+address); 
		
		shift_out_byte(control_byte2);
		shift_out_byte(control_byte1);
		shift_out_byte(control_byte0);
		
		set_bit(PORTB,SHIFT_LATCH_PIN);	// Latch output
		clr_bit(PORTB,SHIFT_LATCH_PIN);
		
		microcode_counter++;
	}
}

