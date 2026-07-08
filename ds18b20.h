#ifndef __DS18B20_H
#define __DS18B20_H

#include "stm32f10x.h"

// ?? DS18B20 ??? GPIO ??(???? PA1,?????)
#define DS18B20_PORT        GPIOA
#define DS18B20_PIN         GPIO_Pin_1
#define DS18B20_PIN_SOURCE  GPIO_PinSource1
#define DS18B20_CLK_ENABLE  RCC_APB2Periph_GPIOA

// ????
void DS18B20_Init(void);
uint8_t DS18B20_Reset(void);
void DS18B20_WriteByte(uint8_t data);
uint8_t DS18B20_ReadByte(void);
float DS18B20_GetTemperature(void);

#endif
