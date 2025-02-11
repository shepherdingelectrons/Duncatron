#include <avr/io.h>
#include <stdio.h>

#define F_CPU 20000000 // 20 MHz
#define BAUDRATE 19200
#define BAUD_PRESCALLER (((F_CPU / (BAUDRATE * 16UL))) - 1)

//https://www.arduino.cc/reference/tr/language/variables/utilities/progmem/

// ATMega328p control logic sketch

#define set_bit(reg,bit) reg|=(1<<bit)
#define clr_bit(reg,bit) reg&=!(1<<bit)
#define tog_bit(reg,bit) reg^=(1<<bit)

// ADC useful definitions

#define SHIFT_DATA_PIN 0	; PB0
#define SHIFT_CLK_PIN 1 	; PB1
#define SHIFT_LATCH_PIN 2	; PB2

#define ADC_PIN 3 // Change to 7 on actual board else use PC3 (databus_QH to test)

// https://avr-guide.github.io/timers-on-the-atmega328/
//#define WGM00 0
//#define WGM01 1
//#define CS01 1
//#define CS00

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
	clr_bit(PORTC,1); // PC1, CLK
	set_bit(PORTC,2); // PC2, DATABUS_READ = High (active low)
	
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

int main(void)
{
	uint16_t clock_ADC; // raw 10-bit ADC value
	char buffer[30];
	setup_pins();
	adc_setup();
	USART_init();
	
	clr_bit(PORTB,0);
	
    /* Replace with your application code */
    while (1) 
    {
		
		if ((ADCSRA & (1<<ADSC))==0) // ADSC bit goes to 0
		{
			clock_ADC = ADC; // 10-bit read
			sprintf(buffer,"ADC:%d",clock_ADC);
			USART_putstring(buffer);
			USART_send(10);
			USART_send(13);
			if (clock_ADC>512)
			{
				set_bit(PORTB,0);
			}
			else
			{
				clr_bit(PORTB,0);
			}
			ADCSRA |= (1<<ADSC) ; //Start a conversion
		}
		/*
		if (USART_ready()){
			char uart_byte = USART_receive();
			///tog_bit(PORTB,0);
			USART_send(uart_byte);
		}*/
		
		
    }
}

