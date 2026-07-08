#include "ds18b20.h"
#include "delay.h"


#define DS18B20_OUT()   { GPIO_InitTypeDef init; init.GPIO_Pin = DS18B20_PIN; init.GPIO_Mode = GPIO_Mode_Out_PP; init.GPIO_Speed = GPIO_Speed_50MHz; GPIO_Init(DS18B20_PORT, &init); }
#define DS18B20_IN()    { GPIO_InitTypeDef init; init.GPIO_Pin = DS18B20_PIN; init.GPIO_Mode = GPIO_Mode_IN_FLOATING; GPIO_Init(DS18B20_PORT, &init); }

#define DS18B20_HIGH()  GPIO_SetBits(DS18B20_PORT, DS18B20_PIN)
#define DS18B20_LOW()   GPIO_ResetBits(DS18B20_PORT, DS18B20_PIN)
#define DS18B20_READ()  GPIO_ReadInputDataBit(DS18B20_PORT, DS18B20_PIN)


void DS18B20_Init(void)
{
    GPIO_InitTypeDef init;
    RCC_APB2PeriphClockCmd(DS18B20_CLK_ENABLE, ENABLE);
    
    init.GPIO_Pin = DS18B20_PIN;
    init.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(DS18B20_PORT, &init);
}


uint8_t DS18B20_Reset(void)
{
    uint8_t presence = 1;
    DS18B20_OUT();
    DS18B20_LOW();
    delay_us(480);      
    DS18B20_HIGH();
    delay_us(60);
    DS18B20_IN();
    presence = DS18B20_READ();  
    delay_us(420);
    return presence;   
}


void DS18B20_WriteByte(uint8_t data)
{
    DS18B20_OUT();
    for (uint8_t i = 0; i < 8; i++) {
        if (data & 0x01) {
            DS18B20_LOW();
            delay_us(2);
            DS18B20_HIGH();
            delay_us(60);
        } else {
            DS18B20_LOW();
            delay_us(60);
            DS18B20_HIGH();
            delay_us(2);
        }
        data >>= 1;
    }
}


uint8_t DS18B20_ReadByte(void)
{
    uint8_t data = 0;
    for (uint8_t i = 0; i < 8; i++) {
        data >>= 1;
        DS18B20_OUT();
        DS18B20_LOW();
        delay_us(2);
        DS18B20_HIGH();
        DS18B20_IN();
        if (DS18B20_READ()) {
            data |= 0x80;
        }
        delay_us(60);
    }
    return data;
}


float DS18B20_GetTemperature(void)
{
    uint8_t tempL, tempH;
    int16_t tempRaw;
    
    if (DS18B20_Reset() != 0) {
        return -100.0f;  
    }
    DS18B20_WriteByte(0xCC);   
    DS18B20_WriteByte(0x44);   
    delay_ms(750);             
    
    if (DS18B20_Reset() != 0) {
        return -100.0f;
    }
    DS18B20_WriteByte(0xCC);
    DS18B20_WriteByte(0xBE);  
    tempL = DS18B20_ReadByte();
    tempH = DS18B20_ReadByte();
    
    tempRaw = (tempH << 8) | tempL;

    if (tempRaw & 0x8000) {
        tempRaw = ~tempRaw + 1;
        return - (float)tempRaw * 0.0625f;
    } else {
        return (float)tempRaw * 0.0625f;
    }
}
