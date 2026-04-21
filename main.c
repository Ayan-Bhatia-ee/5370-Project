#define F_CPU 8000000UL
#include <avr/io.h>
#include <util/delay.h>

int main(void) {
    DDRB |= (1 << PB0);  // trigger
    DDRC = 0x3F;         // PC0-PC5 outputs
    DDRD = 0xFF;         // PD0-PD7 outputs
    
    while(1) {
        // ===== MAXIMUM POWER BURST =====
        PORTB |= (1 << PB0);  // trigger HIGH
        
        // Unrolled aggressive toggling
        for (uint16_t i = 0; i < 5000; i++) {
            PORTC = 0x3F; PORTD = 0xFF;
            PORTC = 0x00; PORTD = 0x00;
            PORTC = 0x3F; PORTD = 0xFF;
            PORTC = 0x00; PORTD = 0x00;
            PORTC = 0x3F; PORTD = 0xFF;
            PORTC = 0x00; PORTD = 0x00;
            PORTC = 0x3F; PORTD = 0xFF;
            PORTC = 0x00; PORTD = 0x00;
        }
        
        PORTB &= ~(1 << PB0);  // trigger LOW
        
        _delay_ms(50);  // long quiet period
    }
}
