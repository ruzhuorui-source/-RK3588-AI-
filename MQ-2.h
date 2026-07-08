#ifndef __MQ2_H
#define __MQ2_H

#include "stm32f10x.h"

#define MQ2_ADC_CHANNEL   ADC_Channel_0   
#define MQ2_ADC_GPIO_PORT GPIOA
#define MQ2_ADC_GPIO_PIN  GPIO_Pin_0
#define MQ2_ADC           ADC1

void MQ2_Init(void);
uint16_t MQ2_ReadRaw(void);
float MQ2_GetVoltage(void);
float MQ2_GetConcentration(void);  

#endif
