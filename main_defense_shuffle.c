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

static uint32_t lfsr_state = 0xACE1BEEF;
static uint32_t shuffle_lfsr = 0xCAFEBABE;

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

static uint8_t shuffle_byte(void) {
    uint8_t out = 0;
    for (uint8_t i = 0; i < 8; i++) {
        uint32_t bit = shuffle_lfsr & 1u;
        shuffle_lfsr >>= 1;
        if (bit) shuffle_lfsr ^= 0xD0000001u;
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
    uint8_t order[16];
    uint8_t dummy_buffer[16];  // For dummy operations
    
    struct AES_ctx ctx;
    AES_init_ctx(&ctx, key);
    
    while (1) {
        for (uint8_t i = 0; i < 16; i++) {
            plaintext[i] = lfsr_byte();
        }
        memcpy(ciphertext, plaintext, 16);
        
        // Generate random permutation (Fisher-Yates)
        for (uint8_t i = 0; i < 16; i++) order[i] = i;
        for (uint8_t i = 15; i > 0; i--) {
            uint8_t j = shuffle_byte() % (i + 1);
            uint8_t tmp = order[i];
            order[i] = order[j];
            order[j] = tmp;
        }
        
        _delay_ms(50);
        
        TRIG_PORT |= (1 << TRIG_PIN);
        
        // Do a "dummy" pre-processing pass over the bytes in random order
        // Each access creates timing-shifted leakage that confuses CPA
        for (uint8_t i = 0; i < 16; i++) {
            uint8_t idx = order[i];
            // Touch the byte (causes load instructions = timing-shifted leakage)
            dummy_buffer[idx] = ciphertext[idx];
            asm volatile ("nop\n nop\n nop\n nop\n");
        }
        
        // Now actual AES (in normal order)
        AES_ECB_encrypt(&ctx, ciphertext);
        TRIG_PORT &= ~(1 << TRIG_PIN);
        
        _delay_ms(100);
    }
}
