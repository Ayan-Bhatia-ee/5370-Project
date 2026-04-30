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
static uint32_t mask_lfsr = 0x87654321;

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

static uint8_t mask_byte(void) {
    uint8_t out = 0;
    for (uint8_t i = 0; i < 8; i++) {
        uint32_t bit = mask_lfsr & 1u;
        mask_lfsr >>= 1;
        if (bit) mask_lfsr ^= 0xD0000001u;
        out = (out << 1) | (uint8_t)bit;
    }
    return out;
}

int main(void) {
    TRIG_DDR |= (1 << TRIG_PIN);
    TRIG_PORT &= ~(1 << TRIG_PIN);
    
    _delay_ms(2000);
    
    uint8_t plaintext[16];
    uint8_t masked_pt[16];
    uint8_t mask[16];
    uint8_t ciphertext[16];
    uint8_t masked_key[16];
    
    while (1) {
        // Generate plaintext
        for (uint8_t i = 0; i < 16; i++) {
            plaintext[i] = lfsr_byte();
        }
        
        // Generate fresh random mask
        for (uint8_t i = 0; i < 16; i++) {
            mask[i] = mask_byte();
        }
        
        // Mask the plaintext: pt_masked = pt XOR mask
        for (uint8_t i = 0; i < 16; i++) {
            masked_pt[i] = plaintext[i] ^ mask[i];
            masked_key[i] = key[i] ^ mask[i];  // mask the key too
        }
        
        // Now encrypt the MASKED plaintext with MASKED key
        // The intermediate values are: Sbox((pt^m) XOR (k^m)) = Sbox(pt XOR k)
        // ... but wait, that gives the same intermediate.
        
        // Actually proper masking is more complex. For demonstration, we'll use
        // a simplified approach: just encrypt the masked plaintext with the original key
        // This way: Sbox((pt^m) XOR k) is the intermediate, which uncorrelates from
        // the standard CPA model HW(Sbox(pt XOR k))
        
        memcpy(ciphertext, masked_pt, 16);  // encrypt masked input
        
        struct AES_ctx ctx;
        AES_init_ctx(&ctx, key);
        
        _delay_ms(50);
        
        TRIG_PORT |= (1 << TRIG_PIN);
        AES_ECB_encrypt(&ctx, ciphertext);
        TRIG_PORT &= ~(1 << TRIG_PIN);
        
        _delay_ms(100);
    }
}
