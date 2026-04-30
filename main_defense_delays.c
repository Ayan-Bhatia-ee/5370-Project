#define F_CPU 16000000UL
#include <avr/io.h>
#include <util/delay.h>
#include <string.h>
#include "aes.h"

#define TRIG_DDR   DDRB
#define TRIG_PORT  PORTB
#define TRIG_PIN   PB0

static const uint8_t key[16] = {
    0x2B, 0x7E, 0x15, 0x16, 0x28, 0xAE, 0xD2, 0xA6,
    0xAB, 0xF7, 0x15, 0x88, 0x09, 0xCF, 0x4F, 0x3C
};

// LFSR for plaintext generation (matches Python)
static uint32_t lfsr_state = 0xACE1BEEF;

// Separate LFSR for random delay generation (different seed so they don't sync)
static uint32_t delay_lfsr = 0x12345678;

static uint8_t lfsr_byte(void) {
    uint8_t out = 0;
    for (uint8_t i = 0; i < 8; i++) {
        uint32_t bit = lfsr_state & 1u;
        lfsr_state >>= 1;
        if (bit) lfsr_state ^= 0xD0000001u;
        out = (out << 1) | (uint8_t)bit;
    }
    return out;
}

static uint8_t random_delay_count(void) {
    // Returns 0-31 (5 bits) for delay length
    uint8_t out = 0;
    for (uint8_t i = 0; i < 5; i++) {
        uint32_t bit = delay_lfsr & 1u;
        delay_lfsr >>= 1;
        if (bit) delay_lfsr ^= 0xD0000001u;
        out = (out << 1) | (uint8_t)bit;
    }
    return out;
}

int main(void) {
    TRIG_DDR |= (1 << TRIG_PIN);
    TRIG_PORT &= ~(1 << TRIG_PIN);
    
    _delay_ms(2000);
    
    uint8_t plaintext[16];
    uint8_t ciphertext[16];
    
    struct AES_ctx ctx;
    AES_init_ctx(&ctx, key);
    
    while (1) {
        for (uint8_t i = 0; i < 16; i++) {
            plaintext[i] = lfsr_byte();
        }
        memcpy(ciphertext, plaintext, 16);
        
        _delay_ms(50);
        
        TRIG_PORT |= (1 << TRIG_PIN);
        
        // ===== RANDOM DELAY (the defense) =====
        // Insert 0-31 NOPs randomly before AES
        uint8_t delay = random_delay_count();
        for (uint8_t d = 0; d < delay; d++) {
            asm volatile ("nop");
            asm volatile ("nop");
            asm volatile ("nop");
            asm volatile ("nop");
        }
        
        AES_ECB_encrypt(&ctx, ciphertext);
        TRIG_PORT &= ~(1 << TRIG_PIN);
        
        _delay_ms(100);
    }
}
